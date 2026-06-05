from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class PatientMatchStatus(StrEnum):
    EXISTING_PATIENT = "EXISTING_PATIENT"
    NO_MATCH = "NO_MATCH"
    AMBIGUOUS = "AMBIGUOUS"


class PatientRecord(BaseModel):
    """A patient as returned from FHIR (or the mock)."""

    model_config = ConfigDict(strict=True)

    patient_id: str
    fhir_id: str
    first_name: str
    last_name: str
    dob: str            # ISO 8601 date YYYY-MM-DD — PHI
    phone: str          # PHI
    email: str | None = None
    postal_code: str | None = None
    is_new: bool
    created_at: str     # ISO 8601


class PatientLookupRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    first_name: str
    last_name: str
    date_of_birth: str  # ISO 8601 date
    phone: str


class PatientLookupResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    status: PatientMatchStatus
    patient: PatientRecord | None = None
    candidates: list[PatientRecord] = []   # populated when status == AMBIGUOUS


class PatientCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    first_name: str
    last_name: str
    date_of_birth: str  # ISO 8601 date
    phone: str
    email: str | None = None
    postal_code: str | None = None
    gender: str | None = None
    consent_ref: str    # data-processing consent must exist before creation


class PatientCreateResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    patient_id: str
    fhir_id: str
    created_at: str     # ISO 8601
