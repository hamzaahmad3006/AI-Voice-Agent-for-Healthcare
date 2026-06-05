from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.appointment import (
    AppointmentStatus,
    BookingRequest,
    SlotResult,
    UrgencyLevel,
    VisitRequest,
)
from models.fsm_state import (
    ConversationSession,
    FSMState,
    LLMTurn,
    SessionSlots,
    ToolCallType,
)
from models.insurance import (
    EligibilityStatus,
    InsuranceCheckResponse,
)
from models.patient import (
    PatientCreateRequest,
    PatientLookupRequest,
    PatientLookupResponse,
    PatientMatchStatus,
    PatientRecord,
)
from models.session_log import (
    ConsentEvent,
    ConsentType,
    ConsentValue,
    SessionLog,
    SessionOutcome,
    TurnLog,
)


class TestFSMStateModel:
    def test_all_twelve_states_defined(self) -> None:
        states = set(FSMState)
        expected = {
            FSMState.GREETING,
            FSMState.CONSENT_DATA,
            FSMState.IDENTIFY,
            FSMState.RETRIEVE_OR_CREATE,
            FSMState.VISIT_INTAKE,
            FSMState.SLOT_SEARCH,
            FSMState.INSURANCE_CHECK,
            FSMState.CONFIRM,
            FSMState.BOOK,
            FSMState.CLOSING,
            FSMState.HUMAN_HANDOFF,
            FSMState.ERROR_FALLBACK,
        }
        assert states == expected

    def test_all_tool_call_types_defined(self) -> None:
        types = set(ToolCallType)
        assert ToolCallType.LOOKUP_PATIENT in types
        assert ToolCallType.CREATE_PATIENT in types
        assert ToolCallType.SEARCH_SLOTS in types
        assert ToolCallType.BOOK_APPOINTMENT in types
        assert ToolCallType.CHECK_INSURANCE in types
        assert ToolCallType.RECORD_CONSENT in types

    def test_llm_turn_no_tool_call(self) -> None:
        turn = LLMTurn(
            intent="provide_name",
            slots={"first_name": "Jane", "last_name": "Doe"},
            response_text="Thank you Jane.",
        )
        assert turn.tool_call is None
        assert turn.slots["first_name"] == "Jane"

    def test_llm_turn_with_tool_call(self) -> None:
        turn = LLMTurn(
            intent="confirm_identity",
            slots={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1985-04-12"},
            response_text="Let me look you up.",
            tool_call={
                "name": ToolCallType.LOOKUP_PATIENT,
                "arguments": {"first_name": "Jane", "last_name": "Doe", "dob": "1985-04-12"},
            },
        )
        assert turn.tool_call is not None
        assert turn.tool_call.name == ToolCallType.LOOKUP_PATIENT

    def test_session_slots_all_default_none(self) -> None:
        slots = SessionSlots()
        assert slots.first_name is None
        assert slots.patient_id is None
        assert slots.data_consent_given is None
        assert slots.booking_consent_given is None
        assert slots.appointment_id is None

    def test_conversation_session_defaults(self) -> None:
        session = ConversationSession(
            session_id="sess-uuid-001",
            room_name="room-001",
            caller_number="+15551234567",
            current_state=FSMState.GREETING,
            slots=SessionSlots(),
            started_at="2026-06-05T10:00:00Z",
        )
        assert session.human_requested is False
        assert session.turn_count == 0


class TestPatientModels:
    def test_lookup_request_valid(self) -> None:
        req = PatientLookupRequest(
            first_name="Jane",
            last_name="Doe",
            date_of_birth="1985-04-12",
            phone="5551234567",
        )
        assert req.first_name == "Jane"
        assert req.date_of_birth == "1985-04-12"

    def test_lookup_response_existing_patient(self) -> None:
        patient = PatientRecord(
            patient_id="pat-001",
            fhir_id="pat-001",
            first_name="Jane",
            last_name="Doe",
            dob="1985-04-12",
            phone="5551234567",
            is_new=False,
            created_at="2026-01-01T00:00:00Z",
        )
        resp = PatientLookupResponse(
            status=PatientMatchStatus.EXISTING_PATIENT,
            patient=patient,
        )
        assert resp.patient is not None
        assert resp.candidates == []
        assert resp.status == PatientMatchStatus.EXISTING_PATIENT

    def test_lookup_response_no_match(self) -> None:
        resp = PatientLookupResponse(status=PatientMatchStatus.NO_MATCH)
        assert resp.patient is None
        assert resp.candidates == []

    def test_create_request_requires_consent_ref(self) -> None:
        with pytest.raises(ValidationError):
            PatientCreateRequest(
                first_name="John",
                last_name="Smith",
                date_of_birth="1990-01-01",
                phone="5559876543",
                # consent_ref intentionally omitted — must raise
            )  # type: ignore[call-arg]

    def test_create_request_valid(self) -> None:
        req = PatientCreateRequest(
            first_name="John",
            last_name="Smith",
            date_of_birth="1990-09-30",
            phone="5559876543",
            consent_ref="consent-001",
        )
        assert req.consent_ref == "consent-001"
        assert req.email is None


class TestAppointmentModels:
    def test_visit_request_defaults(self) -> None:
        req = VisitRequest(reason="Annual checkup", location_id="loc-3")
        assert req.urgency == UrgencyLevel.ROUTINE
        assert req.visit_type == "consult"
        assert req.provider_id is None

    def test_slot_result_valid(self) -> None:
        slot = SlotResult(
            slot_id="slot-9001",
            start="2026-06-09T09:30:00-07:00",
            end="2026-06-09T10:00:00-07:00",
            provider_id="prov-44",
            location_id="loc-3",
        )
        assert slot.slot_id == "slot-9001"

    def test_booking_request_requires_idempotency_key(self) -> None:
        with pytest.raises(ValidationError):
            BookingRequest(
                patient_id="pat-001",
                slot_id="slot-9001",
                reason="Annual checkup",
                consent_ref="consent-001",
                # idempotency_key intentionally omitted — must raise
            )  # type: ignore[call-arg]

    def test_booking_request_valid(self) -> None:
        req = BookingRequest(
            patient_id="pat-001",
            slot_id="slot-9001",
            reason="Annual checkup",
            consent_ref="consent-001",
            idempotency_key="idem-uuid-xyz",
        )
        assert req.idempotency_key == "idem-uuid-xyz"

    def test_appointment_status_values(self) -> None:
        assert AppointmentStatus.BOOKED == "booked"
        assert AppointmentStatus.CANCELLED == "cancelled"
        assert AppointmentStatus.PENDING == "pending"


class TestInsuranceModels:
    def test_eligibility_status_values(self) -> None:
        assert EligibilityStatus.ELIGIBLE == "ELIGIBLE"
        assert EligibilityStatus.INELIGIBLE == "INELIGIBLE"
        assert EligibilityStatus.UNKNOWN == "UNKNOWN"

    def test_check_response_eligible(self) -> None:
        resp = InsuranceCheckResponse(
            eligibility=EligibilityStatus.ELIGIBLE,
            in_network=True,
            plan_name="BlueCross PPO Gold",
            checked_at="2026-06-05T16:40:00Z",
        )
        assert resp.requires_staff_verification is False
        assert resp.in_network is True

    def test_check_response_unknown_sets_staff_flag(self) -> None:
        resp = InsuranceCheckResponse(
            eligibility=EligibilityStatus.UNKNOWN,
            checked_at="2026-06-05T16:40:00Z",
            requires_staff_verification=True,
        )
        assert resp.requires_staff_verification is True
        assert resp.in_network is None


class TestSessionLogModels:
    def test_consent_event_valid(self) -> None:
        event = ConsentEvent(
            type=ConsentType.DATA_PROCESSING,
            value=ConsentValue.YES,
            at="2026-06-05T10:01:00Z",
            transcript_snippet="yes that's fine",
            session_id="sess-001",
        )
        assert event.value == ConsentValue.YES
        assert event.type == ConsentType.DATA_PROCESSING

    def test_session_log_phi_tags_present(self) -> None:
        log = SessionLog(
            session_id="sess-001",
            room_name="room-001",
            caller_number="+15551234567",
            started_at="2026-06-05T10:00:00Z",
            final_state=FSMState.GREETING,
        )
        assert "caller_number" in log.phi_tags
        assert "patient_id" in log.phi_tags

    def test_session_log_empty_collections(self) -> None:
        log = SessionLog(
            session_id="sess-001",
            room_name="room-001",
            caller_number="+15551234567",
            started_at="2026-06-05T10:00:00Z",
            final_state=FSMState.GREETING,
        )
        assert log.turns == []
        assert log.consent_events == []
        assert log.tool_calls == []
        assert log.outcome is None
        assert log.ended_at is None

    def test_turn_log_valid(self) -> None:
        turn = TurnLog(
            n=2,
            state=FSMState.IDENTIFY,
            agent_text="Can I have your full name and date of birth?",
            caller_text="Jane Doe, April 12th 1985",
            latency_ms=1320,
        )
        assert turn.latency_ms == 1320
        assert turn.state == FSMState.IDENTIFY
