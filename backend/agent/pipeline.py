"""Voice pipeline — wires FSM into the LiveKit Agents framework.

Architecture:
    Caller audio  →  Deepgram STT  →  FsmAdapter (our FSM)  →  ElevenLabs TTS  →  Caller audio

FsmAdapter implements livekit.agents.llm.LLM so VoiceAssistant treats our
deterministic FSM exactly like any other LLM, with zero changes to the
livekit-agents framework internals.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from livekit.agents import JobContext, llm as agents_llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import deepgram, silero

from agent.barge_in import DEFAULT_BARGE_IN
from config import settings
from models.fsm_state import ConversationSession, FSMState, SessionSlots
from orchestrator.fsm import FSM, TERMINAL_STATES
from orchestrator.llm_client import GroqLLMClient
from orchestrator.session_memory import SessionMemory
from orchestrator.tool_dispatcher import DomainToolDispatcher

logger = logging.getLogger(__name__)

_GREETING_TEXT = (
    "Hello, thank you for calling. "
    "This is an automated appointment scheduling assistant. "
    "Before we begin, I need to let you know that this call may be recorded "
    "for quality and scheduling purposes. "
    "Do you consent to us collecting and using your information to book an appointment?"
)


# ---------------------------------------------------------------------------
# FSM → livekit-agents LLM adapter
# ---------------------------------------------------------------------------


class FsmStream(agents_llm.LLMStream):
    """Single-response stream — runs one FSM turn and emits the response text."""

    def __init__(
        self,
        *,
        fsm: FSM,
        transcript: str,
        chat_ctx: agents_llm.ChatContext,
        session_ended_event: asyncio.Event,
    ) -> None:
        super().__init__(chat_ctx=chat_ctx, fnc_ctx=None)
        self._fsm = fsm
        self._transcript = transcript
        self._session_ended_event = session_ended_event

    async def _run(self) -> None:
        result = await self._fsm.process_turn(self._transcript)

        # Emit the response as a single chunk (TTS streams it word-by-word).
        self._event_ch.send_nowait(
            agents_llm.ChatChunk(
                choices=[
                    agents_llm.Choice(
                        delta=agents_llm.ChoiceDelta(
                            role="assistant",
                            content=result.response_text,
                        ),
                        index=0,
                    )
                ]
            )
        )

        if result.session_ended:
            # Signal the worker to close the room after TTS finishes.
            self._session_ended_event.set()
            logger.info(
                "Session ended  session_id=%s  final_state=%s",
                self._fsm.session.session_id,
                result.current_state,
            )


class FsmAdapter(agents_llm.LLM):
    """livekit-agents LLM plugin backed by the deterministic FSM.

    One adapter instance per call — owns its own FSM, LLM client, and
    tool dispatcher.  The `session_ended` asyncio.Event fires when the FSM
    reaches a terminal state; the worker awaits it to close the room.
    """

    def __init__(self, session: ConversationSession) -> None:
        super().__init__()
        self._fsm = FSM(
            session=session,
            llm=GroqLLMClient(),
            tools=DomainToolDispatcher(),
        )
        self._memory = SessionMemory()
        self.session_ended: asyncio.Event = asyncio.Event()

    @property
    def fsm(self) -> FSM:
        return self._fsm

    def chat(
        self,
        *,
        chat_ctx: agents_llm.ChatContext,
        fnc_ctx: agents_llm.FunctionContext | None = None,
        temperature: float | None = None,
        n: int | None = 1,
        parallel_tool_calls: bool | None = None,
    ) -> FsmStream:
        # Pull the last caller utterance from the chat history.
        transcript = ""
        for msg in reversed(chat_ctx.messages):
            if msg.role == "user":
                transcript = str(msg.content or "")
                break

        return FsmStream(
            fsm=self._fsm,
            transcript=transcript,
            chat_ctx=chat_ctx,
            session_ended_event=self.session_ended,
        )

    async def persist(self) -> None:
        """Snapshot the current session state to Redis."""
        await self._memory.save(self._fsm.session)

    async def cleanup(self) -> None:
        """Remove session from Redis on call end (TTL would do it too,
        but explicit delete keeps the store clean)."""
        await self._memory.delete(self._fsm.session.session_id)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def new_session(ctx: JobContext) -> ConversationSession:
    """Build a fresh ConversationSession from LiveKit job context."""
    caller_number = (
        ctx.room.metadata  # set by SIP gateway in production
        or "unknown"
    )
    return ConversationSession(
        session_id=str(uuid.uuid4()),
        room_name=ctx.room.name,
        caller_number=caller_number,
        current_state=FSMState.GREETING,
        slots=SessionSlots(),
        started_at=datetime.now(timezone.utc).isoformat(),
    )


def build_voice_assistant(adapter: FsmAdapter) -> VoiceAssistant:
    """Construct a VoiceAssistant wired to the given FSM adapter.

    Plugin notes:
    - VAD:  Silero (bundled, runs locally — no API key needed)
    - STT:  Deepgram streaming (DEEPGRAM_API_KEY required)
    - LLM:  FsmAdapter (our deterministic FSM — not a real LLM)
    - TTS:  ElevenLabs or Cartesia based on TTS_PROVIDER config
    """
    tts = _build_tts()

    cfg = DEFAULT_BARGE_IN
    return VoiceAssistant(
        vad=silero.VAD.load(),
        stt=deepgram.STT(api_key=settings.deepgram_api_key),
        llm=adapter,
        tts=tts,
        interrupt_speech_duration=cfg.interrupt_speech_duration,
        interrupt_min_words=cfg.interrupt_min_words,
        allow_interruptions=cfg.allow_interruptions,
    )


def _build_tts() -> object:
    """Return the configured TTS plugin (ElevenLabs or Cartesia)."""
    if settings.tts_provider.lower() == "cartesia":
        from livekit.plugins import cartesia  # type: ignore[import]
        return cartesia.TTS(api_key=settings.cartesia_api_key)

    # Default: ElevenLabs
    from livekit.plugins import elevenlabs  # type: ignore[import]
    return elevenlabs.TTS(api_key=settings.elevenlabs_api_key)


GREETING_TEXT = _GREETING_TEXT
