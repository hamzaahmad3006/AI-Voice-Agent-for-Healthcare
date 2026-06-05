from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class UrgencyLevel(StrEnum):
    ROUTINE = "routine"
    SOON = "soon"
    URGENT = "urgent"


class AppointmentStatus(StrEnum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    PENDING = "pending"


class VisitRequest(BaseModel):
    """Structured intake collected during VISIT_INTAKE state."""

    model_config = ConfigDict(strict=True)

    reason: str
    location_id: str
    provider_id: str | None = None
    urgency: UrgencyLevel = UrgencyLevel.ROUTINE
    visit_type: str = "consult"


class SlotResult(BaseModel):
    """A single available appointment slot from the scheduling backend."""

    model_config = ConfigDict(strict=True)

    slot_id: str
    start: str      # ISO 8601 datetime
    end: str        # ISO 8601 datetime
    provider_id: str
    location_id: str


class SlotSearchRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    provider_id: str | None = None
    location_id: str
    visit_type: str
    from_date: str  # ISO 8601 date
    to_date: str    # ISO 8601 date


class SlotSearchResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    slots: list[SlotResult]


class BookingRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    patient_id: str
    slot_id: str
    reason: str
    consent_ref: str        # booking consent must exist before this fires
    idempotency_key: str    # prevents double-booking on retry


class AppointmentResponse(BaseModel):
    """Confirmed appointment returned from the scheduling backend."""

    model_config = ConfigDict(strict=True)

    appointment_id: str
    patient_id: str
    provider_id: str
    location_id: str
    slot_id: str
    visit_type: str
    reason: str
    start: str              # ISO 8601 datetime
    end: str                # ISO 8601 datetime
    status: AppointmentStatus
    confirmation_code: str
    consent_ref: str
    created_at: str         # ISO 8601
