from __future__ import annotations

from helpers.fhir_helper import get_patient_by_id
from models.patient import PatientRecord
from orchestrator.session_memory import SessionMemory

_memory = SessionMemory()


async def get_patient_for_session(session_id: str) -> PatientRecord | None:
    """Return the patient record for a session, or None if not yet identified."""
    session = await _memory.load(session_id)
    if session is None:
        return None
    if session.slots.patient_id is None:
        return None
    return await get_patient_by_id(session.slots.patient_id)
