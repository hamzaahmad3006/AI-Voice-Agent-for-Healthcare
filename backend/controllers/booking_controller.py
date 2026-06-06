from __future__ import annotations

from models.appointment import AppointmentStatus, AppointmentSummary
from orchestrator.session_memory import SessionMemory

_memory = SessionMemory()


async def get_booking_status(session_id: str) -> AppointmentSummary | None:
    """Return booking summary for a session, or None if not booked / not found."""
    session = await _memory.load(session_id)
    if session is None:
        return None
    if session.slots.appointment_id is None:
        return None
    return AppointmentSummary(
        session_id=session_id,
        appointment_id=session.slots.appointment_id,
        confirmation_code=session.slots.confirmation_code,
        slot_id=session.slots.selected_slot_id,
        status=AppointmentStatus.BOOKED,
    )
