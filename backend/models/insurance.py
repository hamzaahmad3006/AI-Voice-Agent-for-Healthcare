from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class EligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"     # triggers flag-for-staff path, booking still proceeds


class InsuranceCheckRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    payer_name: str
    member_id: str
    group_number: str | None = None
    patient_dob: str    # ISO 8601 date — PHI
    provider_id: str


class InsuranceCheckResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    eligibility: EligibilityStatus
    in_network: bool | None = None
    plan_name: str | None = None
    checked_at: str     # ISO 8601
    notes: str | None = None
    requires_staff_verification: bool = False  


class Coverage(BaseModel):
    """Persisted coverage record linked to a session."""

    model_config = ConfigDict(strict=True)

    coverage_id: str
    patient_id: str
    payer_name: str
    member_id: str
    group_number: str | None = None
    plan_name: str | None = None
    eligibility: EligibilityStatus
    in_network: bool | None = None
    checked_at: str         # ISO 8601
    verified_by_staff: bool = False
