from __future__ import annotations

from fastapi import APIRouter, HTTPException

from controllers.conversation_controller import (
    SessionStartResponse,
    TurnRequest,
    TurnResponse,
    process_conversation_turn,
    start_session,
)
from controllers.session_controller import get_active_sessions, get_session_detail
from models.session_log import SessionListItem, SessionLog

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionListItem])
async def list_sessions() -> list[SessionListItem]:
    """Return all sessions currently live in Redis."""
    return await get_active_sessions()


@router.post("", response_model=SessionStartResponse, status_code=201)
async def create_session() -> SessionStartResponse:
    """Start a new browser-based conversation session."""
    return await start_session()


@router.get("/{session_id}", response_model=SessionLog)
async def get_session(session_id: str) -> SessionLog:
    """Return full session log for one session."""
    detail = await get_session_detail(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return detail


@router.post("/{session_id}/turn", response_model=TurnResponse)
async def conversation_turn(session_id: str, body: TurnRequest) -> TurnResponse:
    """Process one caller utterance and return the agent response."""
    return await process_conversation_turn(session_id, body.text)
