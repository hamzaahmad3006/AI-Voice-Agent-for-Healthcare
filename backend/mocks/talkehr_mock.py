from __future__ import annotations

import random
import string
import uuid
from datetime import date, datetime, timedelta, timezone

from models.appointment import (
    AppointmentResponse,
    AppointmentStatus,
    BookingRequest,
    SlotResult,
    SlotSearchRequest,
    SlotSearchResponse,
)

# ---------------------------------------------------------------------------
# Slot generation — produce realistic-looking future slots on demand
# ---------------------------------------------------------------------------

_PROVIDERS = ["prov-001", "prov-002", "prov-003"]
_SLOT_DURATION_MINUTES = 30

# Track booked slot IDs so we can simulate slot_taken errors
_booked_slots: set[str] = set()

# Track idempotency keys → AppointmentResponse for safe retries
_idempotency_store: dict[str, AppointmentResponse] = {}

# All confirmed appointments
_appointments: dict[str, AppointmentResponse] = {}


def _generate_slots(
    location_id: str,
    provider_id: str | None,
    from_date: date,
    to_date: date,
    count: int = 6,
) -> list[SlotResult]:
    """Generate `count` evenly-spaced slots between from_date and to_date."""
    slots: list[SlotResult] = []
    delta_days = (to_date - from_date).days or 1
    providers = [provider_id] if provider_id else _PROVIDERS

    for i in range(count):
        day_offset = i % max(delta_days, 1)
        slot_date = from_date + timedelta(days=day_offset)
        hour = 9 + (i * 2) % 8  # 09:00, 11:00, 13:00, 15:00, ...
        start_dt = datetime(
            slot_date.year, slot_date.month, slot_date.day,
            hour, 0, 0, tzinfo=timezone.utc,
        )
        end_dt = start_dt + timedelta(minutes=_SLOT_DURATION_MINUTES)
        slot_id = f"slot-{slot_date.isoformat()}-{hour:02d}00-{i}"

        if slot_id in _booked_slots:
            continue  # skip already-booked slots

        slots.append(SlotResult(
            slot_id=slot_id,
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
            provider_id=providers[i % len(providers)],
            location_id=location_id,
        ))

    return slots


def _random_confirmation_code() -> str:
    return "CONF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


async def search_slots(request: SlotSearchRequest) -> SlotSearchResponse:
    from_date = date.fromisoformat(request.from_date)
    to_date = date.fromisoformat(request.to_date)
    slots = _generate_slots(
        location_id=request.location_id,
        provider_id=request.provider_id,
        from_date=from_date,
        to_date=to_date,
    )
    return SlotSearchResponse(slots=slots)


async def book(request: BookingRequest) -> AppointmentResponse:
    """Book a slot — idempotent on idempotency_key."""
    # Safe retry: same key → same response
    if request.idempotency_key in _idempotency_store:
        return _idempotency_store[request.idempotency_key]

    if request.slot_id in _booked_slots:
        raise SlotTakenError(request.slot_id)

    _booked_slots.add(request.slot_id)

    # Reconstruct slot details from slot_id (format: slot-YYYY-MM-DD-HHmm-N)
    parts = request.slot_id.split("-")
    try:
        slot_date = date.fromisoformat(f"{parts[1]}-{parts[2]}-{parts[3]}")
        hour = int(parts[4][:2])
        minute = int(parts[4][2:])
    except (IndexError, ValueError):
        slot_date = date.today() + timedelta(days=1)
        hour, minute = 9, 0

    start_dt = datetime(
        slot_date.year, slot_date.month, slot_date.day,
        hour, minute, 0, tzinfo=timezone.utc,
    )
    end_dt = start_dt + timedelta(minutes=_SLOT_DURATION_MINUTES)
    now = datetime.now(timezone.utc).isoformat()

    appt = AppointmentResponse(
        appointment_id=f"appt-{uuid.uuid4().hex[:8]}",
        patient_id=request.patient_id,
        provider_id=_PROVIDERS[0],
        location_id="loc-default",
        slot_id=request.slot_id,
        visit_type="consult",
        reason=request.reason,
        start=start_dt.isoformat(),
        end=end_dt.isoformat(),
        status=AppointmentStatus.BOOKED,
        confirmation_code=_random_confirmation_code(),
        consent_ref=request.consent_ref,
        created_at=now,
    )

    _appointments[appt.appointment_id] = appt
    _idempotency_store[request.idempotency_key] = appt
    return appt


def reset() -> None:
    """Reset all state — tests only."""
    _booked_slots.clear()
    _idempotency_store.clear()
    _appointments.clear()


class SlotTakenError(Exception):
    def __init__(self, slot_id: str) -> None:
        super().__init__(f"Slot already booked: {slot_id}")
        self.slot_id = slot_id
