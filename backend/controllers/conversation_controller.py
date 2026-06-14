from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

from models.fsm_state import ConversationSession, FSMState, SessionSlots
from orchestrator.fsm import FSM
from orchestrator.llm_client import GroqLLMClient
from orchestrator.session_memory import SessionMemory
from orchestrator.tool_dispatcher import DomainToolDispatcher

_GREETING = (
    "Hello, thank you for calling VocalHealth AI. "
    "This is your automated appointment scheduling assistant. "
    "Before we begin, I need your consent to collect and process your information "
    "to schedule your appointment. Do you agree?"
)


class SessionStartResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    session_id: str
    greeting: str


class TurnRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    text: str


class TurnResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    response_text: str
    state: str
    session_ended: bool


async def start_session() -> SessionStartResponse:
    session = ConversationSession(
        session_id=str(uuid.uuid4()),
        room_name=f"browser-{uuid.uuid4().hex[:8]}",
        caller_number="browser",
        current_state=FSMState.CONSENT_DATA,
        slots=SessionSlots(),
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    memory = SessionMemory()
    await memory.save(session)
    return SessionStartResponse(session_id=session.session_id, greeting=_GREETING)


async def process_conversation_turn(session_id: str, text: str) -> TurnResponse:
    memory = SessionMemory()
    session = await memory.load(session_id)
    if session is None:
        return TurnResponse(
            response_text=(
                "Your session has expired. Please refresh the page to start a new call."
            ),
            state=str(FSMState.ERROR_FALLBACK),
            session_ended=True,
        )

    fsm = FSM(
        session=session,
        llm=GroqLLMClient(),
        tools=DomainToolDispatcher(),
    )
    try:
        result = await fsm.process_turn(text)
        await memory.save(session)
        return TurnResponse(
            response_text=result.response_text,
            state=str(result.current_state),
            session_ended=result.session_ended,
        )
    except Exception as exc:
        logger.exception("Turn failed for session %s: %s", session_id, exc)
        return TurnResponse(
            response_text=(
                "I'm sorry, I encountered a technical issue. Please try again or say "
                "'talk to a person' to speak with a human agent."
            ),
            state=str(session.current_state),
            session_ended=False,
        )
