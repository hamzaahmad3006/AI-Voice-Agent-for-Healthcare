from __future__ import annotations

import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher

from models.patient import (
    PatientCreateRequest,
    PatientCreateResponse,
    PatientLookupRequest,
    PatientLookupResponse,
    PatientMatchStatus,
    PatientRecord,
)

# ---------------------------------------------------------------------------
# In-memory patient store — seeded with a handful of demo patients
# ---------------------------------------------------------------------------

_SEED_PATIENTS: list[PatientRecord] = [
    PatientRecord(
        patient_id="pat-001",
        fhir_id="fhir-001",
        first_name="Sarah",
        last_name="Johnson",
        dob="1985-04-12",
        phone="5550001001",
        email="sarah.johnson@example.com",
        postal_code="10001",
        is_new=False,
        created_at="2024-01-15T09:00:00Z",
    ),
    PatientRecord(
        patient_id="pat-002",
        fhir_id="fhir-002",
        first_name="Michael",
        last_name="Chen",
        dob="1972-11-30",
        phone="5550001002",
        email="michael.chen@example.com",
        postal_code="90210",
        is_new=False,
        created_at="2024-02-20T14:30:00Z",
    ),
    PatientRecord(
        patient_id="pat-003",
        fhir_id="fhir-003",
        first_name="Emily",
        last_name="Rodriguez",
        dob="1990-07-22",
        phone="5550001003",
        email=None,
        postal_code=None,
        is_new=False,
        created_at="2024-03-05T11:00:00Z",
    ),
]

# Mutable runtime store (starts from seed data)
_patients: dict[str, PatientRecord] = {p.patient_id: p for p in _SEED_PATIENTS}

# Fuzzy-match threshold — 0.80 allows minor STT transcription noise (e.g. "Saraa"→"Sarah")
_MATCH_THRESHOLD = 0.80


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _normalize_phone(phone: str) -> str:
    return "".join(c for c in phone if c.isdigit())


async def lookup(request: PatientLookupRequest) -> PatientLookupResponse:
    """Find patient by name + DOB + phone with fuzzy name matching."""
    req_phone = _normalize_phone(request.phone)

    candidates: list[PatientRecord] = []

    for patient in _patients.values():
        phone_match = _normalize_phone(patient.phone) == req_phone
        dob_match = patient.dob == request.date_of_birth
        first_match = _similarity(patient.first_name, request.first_name) >= _MATCH_THRESHOLD
        last_match = _similarity(patient.last_name, request.last_name) >= _MATCH_THRESHOLD

        # Exact-ish match: all four fields
        if phone_match and dob_match and first_match and last_match:
            return PatientLookupResponse(
                status=PatientMatchStatus.EXISTING_PATIENT,
                patient=patient,
                candidates=[],
            )

        # Partial match: name + dob but phone differs (possible number change)
        if dob_match and first_match and last_match:
            candidates.append(patient)

    if len(candidates) == 1:
        return PatientLookupResponse(
            status=PatientMatchStatus.AMBIGUOUS,
            patient=None,
            candidates=candidates,
        )
    if len(candidates) > 1:
        return PatientLookupResponse(
            status=PatientMatchStatus.AMBIGUOUS,
            patient=None,
            candidates=candidates,
        )

    return PatientLookupResponse(
        status=PatientMatchStatus.NO_MATCH,
        patient=None,
        candidates=[],
    )


async def create(request: PatientCreateRequest) -> PatientCreateResponse:
    """Create a new patient record and persist to in-memory store."""
    patient_id = f"pat-{uuid.uuid4().hex[:8]}"
    fhir_id = f"fhir-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    record = PatientRecord(
        patient_id=patient_id,
        fhir_id=fhir_id,
        first_name=request.first_name,
        last_name=request.last_name,
        dob=request.date_of_birth,
        phone=_normalize_phone(request.phone),
        email=None,
        postal_code=None,
        is_new=True,
        created_at=now,
    )
    _patients[patient_id] = record

    return PatientCreateResponse(
        patient_id=patient_id,
        fhir_id=fhir_id,
        created=True,
        created_at=now,
    )


def get_by_id(patient_id: str) -> PatientRecord | None:
    return _patients.get(patient_id)


def reset() -> None:
    """Reset to seed data — used in tests only."""
    _patients.clear()
    _patients.update({p.patient_id: p for p in _SEED_PATIENTS})
