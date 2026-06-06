from __future__ import annotations

from fastapi import APIRouter, HTTPException

from controllers.session_controller import get_active_sessions, get_session_detail
from models.session_log import SessionListItem, SessionLog

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionListItem])
async def list_sessions() -> list[SessionListItem]:
    """Return all sessions currently live in Redis."""
    return await get_active_sessions()


@router.get("/{session_id}", response_model=SessionLog)
async def get_session(session_id: str) -> SessionLog:
    """Return full session log for one session."""
    detail = await get_session_detail(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return detail
