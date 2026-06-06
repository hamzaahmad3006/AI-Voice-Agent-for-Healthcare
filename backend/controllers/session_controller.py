from __future__ import annotations

from models.fsm_state import ConversationSession
from models.session_log import SessionListItem, SessionLog, TurnLog
from orchestrator.session_memory import SessionMemory

_memory = SessionMemory()


async def get_active_sessions() -> list[SessionListItem]:
    """Return summary rows for all sessions currently live in Redis."""
    sessions = await _memory.list_all()
    return [_to_list_item(s) for s in sessions]


async def get_session_detail(session_id: str) -> SessionLog | None:
    """Return full session log for one session, or None if not found."""
    session = await _memory.load(session_id)
    if session is None:
        return None
    return _to_session_log(session)


def _to_list_item(s: ConversationSession) -> SessionListItem:
    return SessionListItem(
        session_id=s.session_id,
        started_at=s.started_at,
        ended_at=None,
        outcome=None,
        final_state=s.current_state,
        patient_id=s.slots.patient_id,
    )


def _to_session_log(s: ConversationSession) -> SessionLog:
    return SessionLog(
        session_id=s.session_id,
        room_name=s.room_name,
        caller_number=s.caller_number,
        patient_id=s.slots.patient_id,
        started_at=s.started_at,
        ended_at=None,
        outcome=None,
        final_state=s.current_state,
        consent_events=[],
        turns=[],
        tool_calls=[],
        phi_tags=["caller_number", "patient_id"],
    )
