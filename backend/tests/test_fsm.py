"""Unit tests for the FSM engine — pure Python, no external services.

Every test uses synchronous session construction + mock LLM/tool dependencies.
All async tests run under pytest-asyncio.
"""
from __future__ import annotations

import pytest

from models.fsm_state import (
    ConversationSession,
    FSMState,
    LLMToolCall,
    LLMTurn,
    SessionSlots,
    ToolCallType,
)
from orchestrator.fsm import FSM, FSMResult, ToolResult
from orchestrator.states import STATE_HANDLERS, StateHandler


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class MockLLMClient:
    """Returns a pre-configured LLMTurn on every call."""

    def __init__(self, turn: LLMTurn) -> None:
        self._turn = turn
        self.call_count = 0

    async def call(
        self,
        state_handler: StateHandler,
        transcript: str,
        session: ConversationSession,
    ) -> LLMTurn:
        self.call_count += 1
        return self._turn


class MockToolDispatcher:
    """Returns a pre-configured ToolResult on every dispatch."""

    def __init__(self, result: ToolResult) -> None:
        self._result = result
        self.dispatch_count = 0
        self.last_tool: ToolCallType | None = None

    async def dispatch(
        self,
        tool_call: LLMToolCall,
        session: ConversationSession,
    ) -> ToolResult:
        self.dispatch_count += 1
        self.last_tool = tool_call.name
        return self._result


# ---------------------------------------------------------------------------
# Session factory helpers
# ---------------------------------------------------------------------------


def make_session(
    state: FSMState = FSMState.GREETING,
    **slot_overrides: str | bool | None,
) -> ConversationSession:
    slots = SessionSlots(**slot_overrides)
    return ConversationSession(
        session_id="test-session-001",
        room_name="test-room-001",
        caller_number="+15550001234",
        current_state=state,
        slots=slots,
        started_at="2026-06-06T10:00:00Z",
    )


def make_llm_turn(
    intent: str = "generic",
    slots: dict[str, str | None] | None = None,
    response_text: str = "Test response.",
    tool_call: LLMToolCall | None = None,
) -> LLMTurn:
    return LLMTurn(
        intent=intent,
        slots=slots or {},
        response_text=response_text,
        tool_call=tool_call,
    )


def make_fsm(
    session: ConversationSession,
    llm_turn: LLMTurn,
    tool_result: ToolResult | None = None,
) -> tuple[FSM, MockLLMClient, MockToolDispatcher]:
    llm = MockLLMClient(llm_turn)
    tools = MockToolDispatcher(
        tool_result or ToolResult(success=True, slots_to_update={})
    )
    fsm = FSM(session=session, llm=llm, tools=tools)
    return fsm, llm, tools


# ---------------------------------------------------------------------------
# State handler completeness
# ---------------------------------------------------------------------------


def test_all_12_states_have_handlers() -> None:
    for state in FSMState:
        assert state in STATE_HANDLERS, f"Missing handler for {state}"


def test_terminal_states_have_no_transitions() -> None:
    terminal = {FSMState.CLOSING, FSMState.HUMAN_HANDOFF, FSMState.ERROR_FALLBACK}
    for state in terminal:
        handler = STATE_HANDLERS[state]
        assert handler.is_terminal
        assert handler.transitions == []


def test_non_terminal_states_are_not_marked_terminal() -> None:
    non_terminal = set(FSMState) - {
        FSMState.CLOSING,
        FSMState.HUMAN_HANDOFF,
        FSMState.ERROR_FALLBACK,
    }
    for state in non_terminal:
        assert not STATE_HANDLERS[state].is_terminal


# ---------------------------------------------------------------------------
# GREETING
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_greeting_always_transitions_to_consent_data() -> None:
    session = make_session(FSMState.GREETING)
    fsm, llm, _ = make_fsm(session, make_llm_turn("greeting_acknowledged"))

    result = await fsm.process_turn("Hello")

    assert result.previous_state == FSMState.GREETING
    assert result.current_state == FSMState.CONSENT_DATA
    assert result.transitioned
    assert not result.session_ended
    assert llm.call_count == 1


# ---------------------------------------------------------------------------
# CONSENT_DATA
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consent_given_transitions_to_identify() -> None:
    session = make_session(FSMState.CONSENT_DATA)
    fsm, _, _ = make_fsm(session, make_llm_turn("consent_given"))

    result = await fsm.process_turn("Yes, I consent")

    assert result.current_state == FSMState.IDENTIFY
    assert session.slots.data_consent_given is True


@pytest.mark.asyncio
async def test_consent_refused_transitions_to_human_handoff() -> None:
    session = make_session(FSMState.CONSENT_DATA)
    fsm, _, _ = make_fsm(session, make_llm_turn("consent_refused"))

    result = await fsm.process_turn("No, I don't consent")

    assert result.current_state == FSMState.HUMAN_HANDOFF
    assert session.slots.data_consent_given is False
    assert result.session_ended


@pytest.mark.asyncio
async def test_unclear_consent_stays_in_consent_data() -> None:
    session = make_session(FSMState.CONSENT_DATA)
    fsm, _, _ = make_fsm(session, make_llm_turn("unclear"))

    result = await fsm.process_turn("Umm, what do you mean?")

    assert result.current_state == FSMState.CONSENT_DATA
    assert session.slots.data_consent_given is None
    assert not result.transitioned


# ---------------------------------------------------------------------------
# IDENTIFY
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identify_stays_until_lookup_resolves() -> None:
    session = make_session(FSMState.IDENTIFY)
    fsm, _, _ = make_fsm(
        session,
        make_llm_turn(
            "providing_identity",
            slots={"first_name": "Jane", "last_name": "Doe"},
        ),
    )

    result = await fsm.process_turn("My name is Jane Doe")

    # patient_id not set yet → stay in IDENTIFY
    assert result.current_state == FSMState.IDENTIFY
    assert session.slots.first_name == "Jane"
    assert session.slots.last_name == "Doe"


@pytest.mark.asyncio
async def test_identify_transitions_on_existing_patient_found() -> None:
    session = make_session(FSMState.IDENTIFY)
    tool_result = ToolResult(
        success=True,
        slots_to_update={"patient_id": "pat-existing-001", "fhir_id": "fhir-001"},
    )
    llm_turn = make_llm_turn(
        "providing_identity",
        slots={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1985-04-12", "phone": "5550001234"},
        tool_call=LLMToolCall(
            name=ToolCallType.LOOKUP_PATIENT,
            arguments={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1985-04-12", "phone": "5550001234"},
        ),
    )
    fsm, _, tools = make_fsm(session, llm_turn, tool_result)

    result = await fsm.process_turn("Jane Doe, April 12 1985, 555-000-1234")

    assert result.current_state == FSMState.RETRIEVE_OR_CREATE
    assert session.slots.patient_id == "pat-existing-001"
    assert tools.dispatch_count == 1
    assert tools.last_tool == ToolCallType.LOOKUP_PATIENT


@pytest.mark.asyncio
async def test_identify_transitions_on_new_patient() -> None:
    session = make_session(FSMState.IDENTIFY)
    tool_result = ToolResult(
        success=True,
        slots_to_update={"is_new_patient": True},
    )
    llm_turn = make_llm_turn(
        "providing_identity",
        slots={"first_name": "New", "last_name": "Patient", "date_of_birth": "2000-01-01", "phone": "5559999999"},
        tool_call=LLMToolCall(
            name=ToolCallType.LOOKUP_PATIENT,
            arguments={"first_name": "New", "last_name": "Patient", "date_of_birth": "2000-01-01", "phone": "5559999999"},
        ),
    )
    fsm, _, _ = make_fsm(session, llm_turn, tool_result)

    result = await fsm.process_turn("New Patient, January first 2000, 555-999-9999")

    assert result.current_state == FSMState.RETRIEVE_OR_CREATE
    assert session.slots.is_new_patient is True


@pytest.mark.asyncio
async def test_disallowed_tool_in_identify_is_silently_ignored() -> None:
    session = make_session(FSMState.IDENTIFY)
    llm_turn = make_llm_turn(
        "providing_identity",
        tool_call=LLMToolCall(
            name=ToolCallType.BOOK_APPOINTMENT,  # not permitted in IDENTIFY
            arguments={"patient_id": "x"},
        ),
    )
    fsm, _, tools = make_fsm(session, llm_turn)

    await fsm.process_turn("Book me an appointment")

    # Tool must not have been dispatched
    assert tools.dispatch_count == 0


# ---------------------------------------------------------------------------
# RETRIEVE_OR_CREATE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_or_create_transitions_when_patient_id_set() -> None:
    # Existing patient — patient_id already populated from IDENTIFY
    session = make_session(FSMState.RETRIEVE_OR_CREATE, patient_id="pat-001")
    fsm, _, _ = make_fsm(session, make_llm_turn("record_confirmed"))

    result = await fsm.process_turn("Sounds good")

    assert result.current_state == FSMState.VISIT_INTAKE


@pytest.mark.asyncio
async def test_retrieve_or_create_creates_new_patient() -> None:
    session = make_session(
        FSMState.RETRIEVE_OR_CREATE,
        is_new_patient=True,
        first_name="New",
        last_name="Patient",
        date_of_birth="2000-01-01",
        phone="5559999999",
        data_consent_given=True,
    )
    tool_result = ToolResult(
        success=True,
        slots_to_update={"patient_id": "pat-new-001"},
    )
    llm_turn = make_llm_turn(
        "creating_new",
        tool_call=LLMToolCall(
            name=ToolCallType.CREATE_PATIENT,
            arguments={"first_name": "New", "last_name": "Patient", "date_of_birth": "2000-01-01", "phone": "5559999999"},
        ),
    )
    fsm, _, tools = make_fsm(session, llm_turn, tool_result)

    result = await fsm.process_turn("")

    assert result.current_state == FSMState.VISIT_INTAKE
    assert session.slots.patient_id == "pat-new-001"
    assert tools.last_tool == ToolCallType.CREATE_PATIENT


# ---------------------------------------------------------------------------
# VISIT_INTAKE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_visit_intake_stays_until_slots_complete() -> None:
    session = make_session(FSMState.VISIT_INTAKE)
    fsm, _, _ = make_fsm(
        session,
        make_llm_turn("visit_details_incomplete", slots={"reason_for_visit": "Annual checkup"}),
    )

    result = await fsm.process_turn("I need a checkup")

    # location_id still missing
    assert result.current_state == FSMState.VISIT_INTAKE


@pytest.mark.asyncio
async def test_visit_intake_transitions_when_reason_and_location_set() -> None:
    session = make_session(FSMState.VISIT_INTAKE)
    fsm, _, _ = make_fsm(
        session,
        make_llm_turn(
            "visit_details_provided",
            slots={"reason_for_visit": "Annual checkup", "location_id": "loc-downtown"},
        ),
    )

    result = await fsm.process_turn("Annual checkup at the downtown clinic")

    assert result.current_state == FSMState.SLOT_SEARCH
    assert session.slots.reason_for_visit == "Annual checkup"
    assert session.slots.location_id == "loc-downtown"


# ---------------------------------------------------------------------------
# SLOT_SEARCH
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slot_search_stays_until_slot_selected() -> None:
    session = make_session(FSMState.SLOT_SEARCH)
    fsm, _, _ = make_fsm(session, make_llm_turn("no_preference"))

    result = await fsm.process_turn("Any slot is fine")

    assert result.current_state == FSMState.SLOT_SEARCH


@pytest.mark.asyncio
async def test_slot_search_transitions_when_slot_selected() -> None:
    session = make_session(FSMState.SLOT_SEARCH)
    fsm, _, _ = make_fsm(
        session,
        make_llm_turn("slot_selected", slots={"selected_slot_id": "slot-20260607-0900"}),
    )

    result = await fsm.process_turn("I'll take the 9am slot on June 7th")

    assert result.current_state == FSMState.INSURANCE_CHECK
    assert session.slots.selected_slot_id == "slot-20260607-0900"


# ---------------------------------------------------------------------------
# INSURANCE_CHECK
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insurance_check_stays_until_check_complete() -> None:
    session = make_session(FSMState.INSURANCE_CHECK)
    fsm, _, _ = make_fsm(
        session,
        make_llm_turn("insurance_incomplete", slots={"insurer_name": "BlueCross"}),
    )

    result = await fsm.process_turn("BlueCross")

    # member_id not yet given, coverage_checked still False
    assert result.current_state == FSMState.INSURANCE_CHECK


@pytest.mark.asyncio
async def test_insurance_check_transitions_after_tool_runs() -> None:
    session = make_session(
        FSMState.INSURANCE_CHECK,
        insurer_name="BlueCross",
        member_id="MBR12345",
    )
    tool_result = ToolResult(
        success=True,
        slots_to_update={"coverage_checked": True},
    )
    llm_turn = make_llm_turn(
        "insurance_provided",
        tool_call=LLMToolCall(
            name=ToolCallType.CHECK_INSURANCE,
            arguments={"insurer_name": "BlueCross", "member_id": "MBR12345", "patient_id": "pat-001"},
        ),
    )
    fsm, _, tools = make_fsm(session, llm_turn, tool_result)

    result = await fsm.process_turn("My member ID is MBR12345")

    assert result.current_state == FSMState.CONFIRM
    assert session.slots.coverage_checked
    assert tools.last_tool == ToolCallType.CHECK_INSURANCE


@pytest.mark.asyncio
async def test_insurance_failure_is_non_blocking() -> None:
    """A check_insurance tool failure marks coverage_checked so FSM can advance."""
    session = make_session(
        FSMState.INSURANCE_CHECK,
        insurer_name="UnknownPlan",
        member_id="BAD-ID",
    )
    tool_result = ToolResult(
        success=False,
        error_message="service_unavailable",
    )
    llm_turn = make_llm_turn(
        "insurance_provided",
        tool_call=LLMToolCall(
            name=ToolCallType.CHECK_INSURANCE,
            arguments={"insurer_name": "UnknownPlan", "member_id": "BAD-ID", "patient_id": "pat-001"},
        ),
    )
    fsm, _, _ = make_fsm(session, llm_turn, tool_result)

    result = await fsm.process_turn("My plan is UnknownPlan")

    # coverage_checked set to True by _apply_tool_result even on failure
    assert session.slots.coverage_checked
    assert result.current_state == FSMState.CONFIRM


@pytest.mark.asyncio
async def test_no_insurance_intent_sets_self_pay() -> None:
    session = make_session(FSMState.INSURANCE_CHECK)
    # Tool not called because coverage_checked is still False after intent-to-slots
    fsm, _, _ = make_fsm(session, make_llm_turn("no_insurance"))

    await fsm.process_turn("I don't have insurance")

    assert session.slots.insurer_name == "self_pay"


# ---------------------------------------------------------------------------
# CONFIRM
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_booking_consent_given_transitions_to_book() -> None:
    session = make_session(FSMState.CONFIRM)
    fsm, _, _ = make_fsm(session, make_llm_turn("booking_consent_given"))

    result = await fsm.process_turn("Yes, confirm the appointment")

    assert result.current_state == FSMState.BOOK
    assert session.slots.booking_consent_given is True


@pytest.mark.asyncio
async def test_confirm_booking_consent_refused_goes_to_closing() -> None:
    session = make_session(FSMState.CONFIRM)
    fsm, _, _ = make_fsm(session, make_llm_turn("booking_consent_refused"))

    result = await fsm.process_turn("No, cancel it")

    assert result.current_state == FSMState.CLOSING
    assert session.slots.booking_consent_given is False
    assert result.session_ended


@pytest.mark.asyncio
async def test_confirm_change_request_goes_back_to_slot_search() -> None:
    session = make_session(FSMState.CONFIRM)
    fsm, _, _ = make_fsm(session, make_llm_turn("change_request"))

    result = await fsm.process_turn("Actually I want a different time")

    assert result.current_state == FSMState.SLOT_SEARCH
    assert session.slots.change_requested


# ---------------------------------------------------------------------------
# BOOK
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_book_successful_transitions_to_closing() -> None:
    session = make_session(
        FSMState.BOOK,
        booking_consent_given=True,
        selected_slot_id="slot-001",
        patient_id="pat-001",
    )
    tool_result = ToolResult(
        success=True,
        slots_to_update={
            "appointment_id": "appt-999",
            "confirmation_code": "CONF-ABC123",
        },
    )
    llm_turn = make_llm_turn(
        "booking_in_progress",
        tool_call=LLMToolCall(
            name=ToolCallType.BOOK_APPOINTMENT,
            arguments={
                "patient_id": "pat-001",
                "slot_id": "slot-001",
                "visit_type": "checkup",
                "reason": "Annual checkup",
                "consent_ref": "cref-001",
                "idempotency_key": "test-session-001",
            },
        ),
    )
    fsm, _, tools = make_fsm(session, llm_turn, tool_result)

    result = await fsm.process_turn("")

    assert result.current_state == FSMState.CLOSING
    assert session.slots.appointment_id == "appt-999"
    assert session.slots.confirmation_code == "CONF-ABC123"
    assert tools.last_tool == ToolCallType.BOOK_APPOINTMENT
    assert result.session_ended


@pytest.mark.asyncio
async def test_book_slot_taken_goes_back_to_slot_search() -> None:
    session = make_session(
        FSMState.BOOK,
        booking_consent_given=True,
        selected_slot_id="slot-taken",
        patient_id="pat-001",
    )
    tool_result = ToolResult(
        success=False,
        error_message="slot_taken",
    )
    llm_turn = make_llm_turn(
        "booking_in_progress",
        tool_call=LLMToolCall(
            name=ToolCallType.BOOK_APPOINTMENT,
            arguments={
                "patient_id": "pat-001",
                "slot_id": "slot-taken",
                "visit_type": "checkup",
                "reason": "Annual checkup",
                "consent_ref": "cref-001",
                "idempotency_key": "test-session-001",
            },
        ),
    )
    fsm, _, _ = make_fsm(session, llm_turn, tool_result)

    result = await fsm.process_turn("")

    assert result.current_state == FSMState.SLOT_SEARCH
    assert session.slots.slot_taken
    # selected_slot_id is cleared so caller can choose a new one
    assert session.slots.selected_slot_id is None


# ---------------------------------------------------------------------------
# Terminal states — process_turn returns session_ended immediately
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state",
    [FSMState.CLOSING, FSMState.HUMAN_HANDOFF, FSMState.ERROR_FALLBACK],
)
async def test_terminal_states_end_session_immediately(state: FSMState) -> None:
    session = make_session(state)
    fsm, llm, tools = make_fsm(session, make_llm_turn("anything"))

    result = await fsm.process_turn("anything")

    assert result.session_ended
    assert result.current_state == state
    assert not result.transitioned
    # LLM and tools must NOT be called for terminal states
    assert llm.call_count == 0
    assert tools.dispatch_count == 0


# ---------------------------------------------------------------------------
# HARD CONSENT GATE — HUMAN_HANDOFF reachable from every non-terminal state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state",
    [
        FSMState.GREETING,
        FSMState.CONSENT_DATA,
        FSMState.IDENTIFY,
        FSMState.RETRIEVE_OR_CREATE,
        FSMState.VISIT_INTAKE,
        FSMState.SLOT_SEARCH,
        FSMState.INSURANCE_CHECK,
        FSMState.CONFIRM,
        FSMState.BOOK,
    ],
)
async def test_human_handoff_reachable_from_every_non_terminal_state(
    state: FSMState,
) -> None:
    session = make_session(state)
    fsm, _, _ = make_fsm(session, make_llm_turn("request_human"))

    result = await fsm.process_turn("I want to talk to a person")

    assert result.current_state == FSMState.HUMAN_HANDOFF
    assert session.human_requested
    assert result.session_ended


# ---------------------------------------------------------------------------
# Consent gate integrity — booking cannot proceed without booking_consent_given
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_does_not_advance_to_book_without_consent() -> None:
    session = make_session(FSMState.CONFIRM)
    # Intent is generic — no consent_given, no consent_refused
    fsm, _, _ = make_fsm(session, make_llm_turn("unclear"))

    result = await fsm.process_turn("Hmm, let me think")

    assert result.current_state == FSMState.CONFIRM
    assert session.slots.booking_consent_given is None


@pytest.mark.asyncio
async def test_data_consent_gate_blocks_transition_to_identify() -> None:
    session = make_session(FSMState.CONSENT_DATA)
    # Generic intent — data_consent_given stays None
    fsm, _, _ = make_fsm(session, make_llm_turn("unclear"))

    result = await fsm.process_turn("What do you mean?")

    assert result.current_state == FSMState.CONSENT_DATA
    assert session.slots.data_consent_given is None


# ---------------------------------------------------------------------------
# Slot isolation — LLM cannot write to disallowed slots
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_cannot_write_disallowed_slots() -> None:
    """LLM returning a slot that is not in allowed_slots is silently dropped."""
    session = make_session(FSMState.CONSENT_DATA)
    # LLM tries to sneak in patient_id — not in CONSENT_DATA.allowed_slots
    fsm, _, _ = make_fsm(
        session,
        make_llm_turn("consent_given", slots={"patient_id": "evil-override"}),
    )

    await fsm.process_turn("Yes I consent")

    assert session.slots.patient_id is None


# ---------------------------------------------------------------------------
# Turn counter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_count_increments_on_each_process_turn() -> None:
    session = make_session(FSMState.CONSENT_DATA)
    fsm, _, _ = make_fsm(session, make_llm_turn("unclear"))

    assert session.turn_count == 0
    await fsm.process_turn("Hm?")
    assert session.turn_count == 1
    await fsm.process_turn("What?")
    assert session.turn_count == 2


# ---------------------------------------------------------------------------
# FSMResult fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fsm_result_contains_correct_tool_executed() -> None:
    session = make_session(FSMState.IDENTIFY)
    tool_result = ToolResult(
        success=True,
        slots_to_update={"patient_id": "pat-found"},
    )
    llm_turn = make_llm_turn(
        "providing_identity",
        slots={"first_name": "A", "last_name": "B", "date_of_birth": "1990-01-01", "phone": "5550000001"},
        tool_call=LLMToolCall(
            name=ToolCallType.LOOKUP_PATIENT,
            arguments={"first_name": "A"},
        ),
    )
    fsm, _, _ = make_fsm(session, llm_turn, tool_result)

    result = await fsm.process_turn("A B, Jan 1 1990")

    assert result.tool_executed == ToolCallType.LOOKUP_PATIENT
