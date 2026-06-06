"""Unit tests for the agent pipeline.

Tests cover:
- FsmAdapter.chat() routes transcript to FSM and returns response text
- Session-ended event fires when FSM reaches a terminal state
- new_session() builds a valid ConversationSession
- BargeInConfig defaults are sensible

All tests are pure Python — no LiveKit server required.
livekit-agents is stubbed at the sys.modules level so these tests run even
when the package is not installed in the environment.
"""
from __future__ import annotations

import asyncio
import sys
import types
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub out the entire livekit namespace BEFORE importing agent.pipeline.
# This lets us test FSM/pipeline logic without a real livekit installation.
# ---------------------------------------------------------------------------

def _make_livekit_stubs() -> None:
    """Inject minimal mock objects so agent.pipeline can be imported."""
    if "livekit" in sys.modules:
        return  # real package already present — no stub needed

    # Base LLM class stub — FsmAdapter and FsmStream inherit from these.
    class _LLM:
        def __init__(self, *a: object, **kw: object) -> None: ...
        def chat(self, **kw: object) -> object: ...  # noqa: ANN001

    class _LLMStream:
        def __init__(self, *, chat_ctx: object, fnc_ctx: object) -> None:
            self._chat_ctx = chat_ctx
            self._fnc_ctx = fnc_ctx
            self._event_ch = _FakeChan()

    class _FakeChan:
        def __init__(self) -> None:
            self.sent: list[object] = []
        def send_nowait(self, item: object) -> None:
            self.sent.append(item)

    class _ChatChunk:
        def __init__(self, *, choices: list[object]) -> None:
            self.choices = choices

    class _Choice:
        def __init__(self, *, delta: object, index: int = 0) -> None:
            self.delta = delta
            self.index = index

    class _ChoiceDelta:
        def __init__(self, *, role: str, content: str) -> None:
            self.role = role
            self.content = content

    class _ChatContext:
        def __init__(self) -> None:
            self.messages: list[object] = []

    llm_mod = types.ModuleType("livekit.agents.llm")
    llm_mod.LLM = _LLM  # type: ignore[attr-defined]
    llm_mod.LLMStream = _LLMStream  # type: ignore[attr-defined]
    llm_mod.ChatChunk = _ChatChunk  # type: ignore[attr-defined]
    llm_mod.Choice = _Choice  # type: ignore[attr-defined]
    llm_mod.ChoiceDelta = _ChoiceDelta  # type: ignore[attr-defined]
    llm_mod.ChatContext = _ChatContext  # type: ignore[attr-defined]
    llm_mod.FunctionContext = object  # type: ignore[attr-defined]

    agents_mod = types.ModuleType("livekit.agents")
    agents_mod.llm = llm_mod  # type: ignore[attr-defined]
    agents_mod.JobContext = MagicMock  # type: ignore[attr-defined]
    agents_mod.AutoSubscribe = MagicMock  # type: ignore[attr-defined]
    agents_mod.WorkerOptions = MagicMock  # type: ignore[attr-defined]
    agents_mod.cli = MagicMock()  # type: ignore[attr-defined]

    va_mod = types.ModuleType("livekit.agents.voice_assistant")
    va_mod.VoiceAssistant = MagicMock  # type: ignore[attr-defined]

    livekit_mod = types.ModuleType("livekit")
    livekit_mod.agents = agents_mod  # type: ignore[attr-defined]

    plugins_mod = types.ModuleType("livekit.plugins")
    for plugin in ("deepgram", "silero", "elevenlabs", "cartesia"):
        pm = types.ModuleType(f"livekit.plugins.{plugin}")
        pm.STT = MagicMock  # type: ignore[attr-defined]
        pm.TTS = MagicMock  # type: ignore[attr-defined]
        pm.VAD = MagicMock()  # type: ignore[attr-defined]
        pm.VAD.load = MagicMock(return_value=MagicMock())
        setattr(plugins_mod, plugin, pm)
        sys.modules[f"livekit.plugins.{plugin}"] = pm

    sys.modules["livekit"] = livekit_mod
    sys.modules["livekit.agents"] = agents_mod
    sys.modules["livekit.agents.llm"] = llm_mod
    sys.modules["livekit.agents.voice_assistant"] = va_mod
    sys.modules["livekit.plugins"] = plugins_mod


def _make_dep_stubs() -> None:
    """Stub every uninstalled package that agent.pipeline pulls in transitively."""
    stubs: dict[str, dict[str, object]] = {
        "groq": {"AsyncGroq": MagicMock, "APIError": Exception, "APITimeoutError": TimeoutError},
        "redis": {},
        "redis.asyncio": {"from_url": MagicMock(return_value=MagicMock())},
        "structlog": {"get_logger": MagicMock(return_value=MagicMock())},
    }
    for mod_name, attrs in stubs.items():
        if mod_name not in sys.modules:
            mod = types.ModuleType(mod_name)
            for k, v in attrs.items():
                setattr(mod, k, v)
            sys.modules[mod_name] = mod


_make_livekit_stubs()
_make_dep_stubs()

# Now safe to import agent modules.
from agent.barge_in import BargeInConfig, DEFAULT_BARGE_IN  # noqa: E402
from agent.pipeline import FsmAdapter, FsmStream, new_session  # noqa: E402
from models.fsm_state import ConversationSession, FSMState, SessionSlots  # noqa: E402
from orchestrator.fsm import FSMResult  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chat_ctx(user_text: str) -> MagicMock:
    msg = MagicMock()
    msg.role = "user"
    msg.content = user_text
    ctx = MagicMock()
    ctx.messages = [msg]
    return ctx


def make_session(state: FSMState = FSMState.CONSENT_DATA) -> ConversationSession:
    return ConversationSession(
        session_id=str(uuid.uuid4()),
        room_name="test-room",
        caller_number="5550001234",
        current_state=state,
        slots=SessionSlots(),
        started_at="2026-06-06T10:00:00Z",
    )


# ---------------------------------------------------------------------------
# BargeInConfig
# ---------------------------------------------------------------------------


def test_barge_in_config_defaults_are_sensible() -> None:
    cfg = BargeInConfig()
    assert cfg.interrupt_speech_duration > 0
    assert cfg.interrupt_min_words >= 0
    assert cfg.allow_interruptions is True


def test_default_barge_in_singleton_is_frozen() -> None:
    with pytest.raises((TypeError, AttributeError)):
        DEFAULT_BARGE_IN.allow_interruptions = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# new_session
# ---------------------------------------------------------------------------


def test_new_session_creates_greeting_state() -> None:
    fake_ctx = MagicMock()
    fake_ctx.room.name = "room-001"
    fake_ctx.room.metadata = "+15550001234"

    session = new_session(fake_ctx)

    assert session.current_state == FSMState.GREETING
    assert session.room_name == "room-001"
    assert session.caller_number == "+15550001234"
    assert session.session_id
    assert session.turn_count == 0


def test_new_session_uses_unknown_when_no_metadata() -> None:
    fake_ctx = MagicMock()
    fake_ctx.room.name = "room-002"
    fake_ctx.room.metadata = None

    session = new_session(fake_ctx)
    assert session.caller_number == "unknown"


# ---------------------------------------------------------------------------
# FsmAdapter — chat() routes transcript to FSM
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fsm_adapter_chat_returns_fsm_stream() -> None:
    session = make_session(FSMState.CONSENT_DATA)
    adapter = FsmAdapter.__new__(FsmAdapter)
    adapter.session_ended = asyncio.Event()

    mock_fsm = MagicMock()
    mock_fsm.session = session
    adapter._fsm = mock_fsm
    adapter._memory = MagicMock()

    chat_ctx = _make_chat_ctx("yes I agree")
    stream = adapter.chat(chat_ctx=chat_ctx)

    assert isinstance(stream, FsmStream)
    assert stream._transcript == "yes I agree"


@pytest.mark.asyncio
async def test_fsm_stream_run_pushes_response_chunk() -> None:
    session = make_session()
    ended_event = asyncio.Event()

    mock_result = FSMResult(
        response_text="Please say yes or no.",
        previous_state=FSMState.CONSENT_DATA,
        current_state=FSMState.CONSENT_DATA,
        transitioned=False,
        session_ended=False,
    )
    mock_fsm = MagicMock()
    mock_fsm.process_turn = AsyncMock(return_value=mock_result)
    mock_fsm.session = session

    stream = FsmStream.__new__(FsmStream)
    stream._fsm = mock_fsm
    stream._transcript = "hello"
    stream._chat_ctx = MagicMock()
    stream._session_ended_event = ended_event

    # Use a plain list as the event channel
    sent: list[object] = []
    ch = MagicMock()
    ch.send_nowait = lambda item: sent.append(item)
    stream._event_ch = ch

    await stream._run()

    assert len(sent) == 1
    assert sent[0].choices[0].delta.content == "Please say yes or no."
    assert not ended_event.is_set()


@pytest.mark.asyncio
async def test_fsm_stream_fires_session_ended_on_terminal_state() -> None:
    session = make_session(FSMState.CLOSING)
    ended_event = asyncio.Event()

    mock_result = FSMResult(
        response_text="Goodbye!",
        previous_state=FSMState.BOOK,
        current_state=FSMState.CLOSING,
        transitioned=True,
        session_ended=True,
    )
    mock_fsm = MagicMock()
    mock_fsm.process_turn = AsyncMock(return_value=mock_result)
    mock_fsm.session = session

    stream = FsmStream.__new__(FsmStream)
    stream._fsm = mock_fsm
    stream._transcript = "thanks"
    stream._chat_ctx = MagicMock()
    stream._session_ended_event = ended_event
    sent: list[object] = []
    ch = MagicMock()
    ch.send_nowait = lambda item: sent.append(item)
    stream._event_ch = ch

    await stream._run()

    assert ended_event.is_set()


@pytest.mark.asyncio
async def test_fsm_adapter_uses_empty_transcript_when_no_user_message() -> None:
    session = make_session()
    adapter = FsmAdapter.__new__(FsmAdapter)
    adapter.session_ended = asyncio.Event()
    adapter._fsm = MagicMock()
    adapter._fsm.session = session
    adapter._memory = MagicMock()

    assistant_msg = MagicMock()
    assistant_msg.role = "assistant"
    assistant_msg.content = "Hello"
    ctx = MagicMock()
    ctx.messages = [assistant_msg]

    stream = adapter.chat(chat_ctx=ctx)
    assert stream._transcript == ""


# ---------------------------------------------------------------------------
# FsmAdapter — session lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fsm_adapter_persist_saves_to_redis() -> None:
    session = make_session()
    adapter = FsmAdapter.__new__(FsmAdapter)
    adapter.session_ended = asyncio.Event()
    adapter._fsm = MagicMock()
    adapter._fsm.session = session

    mock_memory = MagicMock()
    mock_memory.save = AsyncMock()
    adapter._memory = mock_memory

    await adapter.persist()
    mock_memory.save.assert_called_once_with(session)


@pytest.mark.asyncio
async def test_fsm_adapter_cleanup_deletes_from_redis() -> None:
    session = make_session()
    adapter = FsmAdapter.__new__(FsmAdapter)
    adapter.session_ended = asyncio.Event()
    adapter._fsm = MagicMock()
    adapter._fsm.session = session

    mock_memory = MagicMock()
    mock_memory.delete = AsyncMock()
    adapter._memory = mock_memory

    await adapter.cleanup()
    mock_memory.delete.assert_called_once_with(session.session_id)
