"""Unit tests for DomainToolDispatcher.

All external calls go to mock services (USE_MOCK_* = true in config defaults).
No network, no Redis, no real FHIR/Talkehr/insurance calls.
"""
from __future__ import annotations

import pytest

from mocks import fhir_mock, talkehr_mock
from models.fsm_state import (
    ConversationSession,
    FSMState,
    LLMToolCall,
    SessionSlots,
    ToolCallType,
)
from orchestrator.tool_dispatcher import DomainToolDispatcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_session(
    state: FSMState = FSMState.IDENTIFY,
    **slot_overrides: object,
) -> ConversationSession:
    slots = SessionSlots(**slot_overrides)  # type: ignore[arg-type]
    return ConversationSession(
        session_id="sess-test-001",
        room_name="room-test-001",
        caller_number="+15550001234",
        current_state=state,
        slots=slots,
        started_at="2026-06-06T10:00:00Z",
    )


def tool_call(name: ToolCallType, **args: object) -> LLMToolCall:
    return LLMToolCall(name=name, arguments=args)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def reset_mocks() -> None:
    fhir_mock.reset()
    talkehr_mock.reset()


dispatcher = DomainToolDispatcher()


# ---------------------------------------------------------------------------
# LOOKUP_PATIENT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_lookup_existing_patient_sets_patient_id() -> None:
    session = make_session(
        first_name="Sarah",
        last_name="Johnson",
        date_of_birth="1985-04-12",
        phone="5550001001",
    )
    result = await dispatcher.dispatch(
        tool_call(ToolCallType.LOOKUP_PATIENT),
        session,
    )

    assert result.success is True
    assert result.slots_to_update["patient_id"] == "pat-001"
    assert result.slots_to_update["is_new_patient"] is False


@pytest.mark.asyncio
async def test_dispatch_lookup_new_patient_sets_is_new_patient() -> None:
    session = make_session(
        first_name="Ghost",
        last_name="Person",
        date_of_birth="2000-01-01",
        phone="0000000000",
    )
    result = await dispatcher.dispatch(
        tool_call(ToolCallType.LOOKUP_PATIENT),
        session,
    )

    assert result.success is True
    assert result.slots_to_update["is_new_patient"] is True


@pytest.mark.asyncio
async def test_dispatch_lookup_missing_slots_fails_gracefully() -> None:
    session = make_session(first_name="Sarah")  # missing last_name, dob, phone
    result = await dispatcher.dispatch(
        tool_call(ToolCallType.LOOKUP_PATIENT),
        session,
    )

    assert result.success is False
    assert result.error_message == "missing_identity_slots"


# ---------------------------------------------------------------------------
# CREATE_PATIENT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_create_patient_returns_new_patient_id() -> None:
    session = make_session(
        first_name="New",
        last_name="User",
        date_of_birth="1990-05-10",
        phone="5551112222",
        data_consent_ref="cref-test-data",
    )
    result = await dispatcher.dispatch(
        tool_call(ToolCallType.CREATE_PATIENT),
        session,
    )

    assert result.success is True
    assert result.slots_to_update["patient_id"].startswith("pat-")
    assert result.slots_to_update["fhir_id"].startswith("fhir-")
    assert result.slots_to_update["is_new_patient"] is True


# ---------------------------------------------------------------------------
# SEARCH_SLOTS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_search_slots_returns_slots_json() -> None:
    import json

    session = make_session(
        state=FSMState.SLOT_SEARCH,
        location_id="loc-downtown",
        visit_type="consult",
        provider_id="prov-001",
    )
    result = await dispatcher.dispatch(
        tool_call(ToolCallType.SEARCH_SLOTS),
        session,
    )

    assert result.success is True
    slots_json = result.slots_to_update.get("available_slots_json")
    assert isinstance(slots_json, str)
    slots = json.loads(slots_json)
    assert len(slots) > 0
    assert "slot_id" in slots[0]


# ---------------------------------------------------------------------------
# BOOK_APPOINTMENT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_book_appointment_returns_confirmation() -> None:
    from datetime import date, timedelta

    from mocks.talkehr_mock import search_slots as mock_search
    from models.appointment import SlotSearchRequest

    # Fetch a real slot from the mock
    today = date.today()
    search_resp = await mock_search(SlotSearchRequest(
        location_id="loc-default",
        visit_type="consult",
        from_date=today.isoformat(),
        to_date=(today + timedelta(days=14)).isoformat(),
    ))
    slot_id = search_resp.slots[0].slot_id

    session = make_session(
        state=FSMState.BOOK,
        patient_id="pat-001",
        selected_slot_id=slot_id,
        reason_for_visit="Annual checkup",
        booking_consent_ref="cref-booking-001",
        booking_consent_given=True,
    )
    result = await dispatcher.dispatch(
        tool_call(ToolCallType.BOOK_APPOINTMENT),
        session,
    )

    assert result.success is True
    assert result.slots_to_update["appointment_id"].startswith("appt-")
    assert result.slots_to_update["confirmation_code"].startswith("CONF-")


@pytest.mark.asyncio
async def test_dispatch_book_slot_taken_returns_slot_taken_error() -> None:
    from datetime import date, timedelta

    from mocks.talkehr_mock import book as mock_book
    from mocks.talkehr_mock import search_slots as mock_search
    from models.appointment import BookingRequest, SlotSearchRequest

    today = date.today()
    search_resp = await mock_search(SlotSearchRequest(
        location_id="loc-default",
        visit_type="consult",
        from_date=today.isoformat(),
        to_date=(today + timedelta(days=14)).isoformat(),
    ))
    slot_id = search_resp.slots[0].slot_id

    # Book it directly via mock first
    await mock_book(BookingRequest(
        patient_id="pat-001",
        slot_id=slot_id,
        reason="First booking",
        consent_ref="cref-a",
        idempotency_key="idem-first",
    ))

    # Now try to book the same slot via dispatcher with different idempotency key
    session = make_session(
        state=FSMState.BOOK,
        patient_id="pat-002",
        selected_slot_id=slot_id,
        reason_for_visit="Second booking",
        booking_consent_given=True,
    )
    # Override session_id to get a different idempotency key
    session.session_id = "sess-test-002"

    result = await dispatcher.dispatch(
        tool_call(ToolCallType.BOOK_APPOINTMENT),
        session,
    )

    assert result.success is False
    assert result.error_message == "slot_taken"


# ---------------------------------------------------------------------------
# CHECK_INSURANCE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_check_insurance_sets_coverage_checked() -> None:
    session = make_session(
        state=FSMState.INSURANCE_CHECK,
        insurer_name="Aetna",
        member_id="MBR-12345",
        date_of_birth="1985-04-12",
        provider_id="prov-001",
    )
    result = await dispatcher.dispatch(
        tool_call(ToolCallType.CHECK_INSURANCE),
        session,
    )

    assert result.success is True
    assert result.slots_to_update["coverage_checked"] is True


@pytest.mark.asyncio
async def test_dispatch_check_insurance_always_succeeds_regardless_of_eligibility() -> None:
    # Even for unknown/ineligible payers, dispatcher returns success=True
    # so FSM advances to CONFIRM (booking is non-blocking on insurance).
    session = make_session(
        state=FSMState.INSURANCE_CHECK,
        insurer_name="no_coverage",
        member_id="MBR-000",
        date_of_birth="1990-01-01",
        provider_id="prov-001",
    )
    result = await dispatcher.dispatch(
        tool_call(ToolCallType.CHECK_INSURANCE),
        session,
    )

    assert result.success is True
    assert result.slots_to_update["coverage_checked"] is True


# ---------------------------------------------------------------------------
# RECORD_CONSENT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_record_data_consent_returns_consent_ref() -> None:
    session = make_session(
        state=FSMState.CONSENT_DATA,
        data_consent_given=False,  # not yet given — will record data consent
    )
    result = await dispatcher.dispatch(
        tool_call(ToolCallType.RECORD_CONSENT, transcript_snippet="yes I agree"),
        session,
    )

    assert result.success is True
    assert "data_consent_ref" in result.slots_to_update
    ref = result.slots_to_update["data_consent_ref"]
    assert isinstance(ref, str) and ref.startswith("cref-")


@pytest.mark.asyncio
async def test_dispatch_record_booking_consent_returns_booking_ref() -> None:
    session = make_session(
        state=FSMState.CONFIRM,
        data_consent_given=True,   # data consent already done
        booking_consent_given=True,
    )
    result = await dispatcher.dispatch(
        tool_call(ToolCallType.RECORD_CONSENT, transcript_snippet="yes book it"),
        session,
    )

    assert result.success is True
    assert "booking_consent_ref" in result.slots_to_update


# ---------------------------------------------------------------------------
# Unknown tool call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_returns_failure() -> None:
    session = make_session()
    tc = LLMToolCall(name=ToolCallType.LOOKUP_PATIENT, arguments={})
    # Monkey-patch name to simulate unknown
    object.__setattr__(tc, "name", "totally_unknown_tool")  # type: ignore[arg-type]

    result = await dispatcher.dispatch(tc, session)

    assert result.success is False
