"""End-to-end integration test — full mock call flow.

Drives the FSM from GREETING all the way to CLOSING using:
  - Real FSM engine (orchestrator/fsm.py)
  - Real DomainToolDispatcher (orchestrator/tool_dispatcher.py)
  - Real in-memory mocks (mocks/fhir_mock.py, talkehr_mock.py, insurance_mock.py)
  - Mocked GroqLLMClient — deterministic LLMTurn per turn

No LiveKit server, no Redis, no real API keys required.

Happy path: existing patient Sarah Johnson (pat-001 in seed data)
flows through GREETING → CONSENT_DATA → IDENTIFY → RETRIEVE_OR_CREATE
→ VISIT_INTAKE → SLOT_SEARCH → INSURANCE_CHECK → CONFIRM → BOOK → CLOSING.
"""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from mocks import fhir_mock, talkehr_mock
from models.fsm_state import (
    ConversationSession,
    FSMState,
    LLMToolCall,
    LLMTurn,
    SessionSlots,
    ToolCallType,
)
from orchestrator.fsm import FSM, TERMINAL_STATES
from orchestrator.tool_dispatcher import DomainToolDispatcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session() -> ConversationSession:
    return ConversationSession(
        session_id=str(uuid.uuid4()),
        room_name="e2e-test-room",
        caller_number="5550001001",
        current_state=FSMState.GREETING,
        slots=SessionSlots(),
        started_at="2026-06-06T10:00:00Z",
    )


def _llm_turn(
    intent: str,
    response_text: str,
    slots: dict[str, str | None] | None = None,
    tool_call: LLMToolCall | None = None,
) -> LLMTurn:
    return LLMTurn(
        intent=intent,
        slots=slots or {},
        response_text=response_text,
        tool_call=tool_call,
    )


def _tc(name: ToolCallType, **kwargs: str | None) -> LLMToolCall:
    return LLMToolCall(name=name, arguments=dict(kwargs))


# ---------------------------------------------------------------------------
# LLM turn sequence for the full happy path
# ---------------------------------------------------------------------------


def _build_llm_sequence(session_id: str) -> list[LLMTurn]:
    today = date.today().isoformat()
    first_slot_id = f"slot-{today}-0900-0"

    return [
        # Turn 1 — GREETING → CONSENT_DATA
        _llm_turn(
            "greeting_acknowledged",
            "Hello! I'm your automated scheduling assistant. Do you consent to collecting your information?",
        ),
        # Turn 2 — CONSENT_DATA → IDENTIFY
        _llm_turn(
            "consent_given",
            "Thank you. Could I have your full name, date of birth, and phone number?",
        ),
        # Turn 3 — IDENTIFY → RETRIEVE_OR_CREATE (lookup_patient tool call)
        _llm_turn(
            "providing_identity",
            "Let me look you up in our system.",
            slots={
                "first_name": "Sarah",
                "last_name": "Johnson",
                "date_of_birth": "1985-04-12",
                "phone": "5550001001",
            },
            tool_call=_tc(
                ToolCallType.LOOKUP_PATIENT,
                first_name="Sarah",
                last_name="Johnson",
                date_of_birth="1985-04-12",
                phone="5550001001",
            ),
        ),
        # Turn 4 — RETRIEVE_OR_CREATE → VISIT_INTAKE
        _llm_turn(
            "record_confirmed",
            "I found your record, Sarah. What brings you in today and which location works best?",
        ),
        # Turn 5 — VISIT_INTAKE → SLOT_SEARCH
        _llm_turn(
            "visit_details_provided",
            "Got it. Let me search for available slots.",
            slots={
                "reason_for_visit": "annual checkup",
                "location_id": "loc-downtown",
                "urgency": "routine",
                "visit_type": "consult",
            },
        ),
        # Turn 6 — SLOT_SEARCH: fetch slots (stays in SLOT_SEARCH after this turn)
        _llm_turn(
            "no_preference",
            "Let me check available slots for you.",
            tool_call=_tc(
                ToolCallType.SEARCH_SLOTS,
                location_id="loc-downtown",
                visit_type="consult",
                urgency="routine",
                provider_id=None,
            ),
        ),
        # Turn 7 — SLOT_SEARCH: select slot → INSURANCE_CHECK
        _llm_turn(
            "slot_selected",
            "I've selected the 9 AM slot.",
            slots={"selected_slot_id": first_slot_id},
        ),
        # Turn 8 — INSURANCE_CHECK → CONFIRM (check_insurance tool call)
        _llm_turn(
            "insurance_provided",
            "Let me verify your insurance now.",
            slots={
                "insurer_name": "BlueCross",
                "member_id": "MBR12345",
                "group_number": None,
            },
            tool_call=_tc(
                ToolCallType.CHECK_INSURANCE,
                insurer_name="BlueCross",
                member_id="MBR12345",
                group_number=None,
                patient_id="pat-001",
            ),
        ),
        # Turn 9 — CONFIRM → BOOK
        _llm_turn(
            "booking_consent_given",
            "Confirmed. Booking your appointment now.",
        ),
        # Turn 10 — BOOK → CLOSING (book_appointment tool call)
        _llm_turn(
            "booking_in_progress",
            "Booking your appointment — one moment please.",
            tool_call=_tc(
                ToolCallType.BOOK_APPOINTMENT,
                patient_id="pat-001",
                slot_id=first_slot_id,
                reason="annual checkup",
                consent_ref="cref-test",
                idempotency_key=session_id,
            ),
        ),
        # Turn 11 — CLOSING is terminal; FSM returns immediately without calling LLM
    ]


# ---------------------------------------------------------------------------
# Happy-path test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_call_flow_reaches_closing_with_booking() -> None:
    """Complete 11-turn call: GREETING → … → CLOSING with confirmed booking."""
    fhir_mock.reset()
    talkehr_mock.reset()

    session = _make_session()
    llm_turns = _build_llm_sequence(session.session_id)

    mock_llm = AsyncMock()
    mock_llm.call.side_effect = llm_turns

    fsm = FSM(session=session, llm=mock_llm, tools=DomainToolDispatcher())

    # -- Simulate turns until terminal state or guard loop --------------
    state_path: list[FSMState] = [session.current_state]
    last_result = None

    for turn_idx in range(12):  # safety cap
        result = await fsm.process_turn(f"caller utterance {turn_idx + 1}")
        last_result = result
        state_path.append(result.current_state)

        if result.session_ended:
            break

    assert last_result is not None
    assert last_result.session_ended, "FSM should have reached a terminal state"
    assert session.current_state == FSMState.CLOSING

    # Booking must be confirmed
    assert session.slots.appointment_id is not None, "appointment_id should be set"
    assert session.slots.confirmation_code is not None, "confirmation_code should be set"
    assert session.slots.confirmation_code.startswith("CONF-")

    # Consent gates must have been crossed
    assert session.slots.data_consent_given is True
    assert session.slots.booking_consent_given is True

    # State path must go through all expected states
    expected_states = [
        FSMState.GREETING,
        FSMState.CONSENT_DATA,
        FSMState.IDENTIFY,
        FSMState.RETRIEVE_OR_CREATE,
        FSMState.VISIT_INTAKE,
        FSMState.SLOT_SEARCH,
        FSMState.SLOT_SEARCH,   # two turns: fetch + select
        FSMState.INSURANCE_CHECK,
        FSMState.CONFIRM,
        FSMState.BOOK,
        FSMState.CLOSING,
    ]
    assert state_path == expected_states


# ---------------------------------------------------------------------------
# Human-escalation path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_human_request_routes_to_handoff_from_any_state() -> None:
    """Saying 'talk to a person' in IDENTIFY triggers HUMAN_HANDOFF."""
    session = _make_session()
    # Jump to IDENTIFY to skip GREETING/CONSENT turns
    session.current_state = FSMState.IDENTIFY
    session.slots = session.slots.model_copy(update={"data_consent_given": True})

    mock_llm = AsyncMock()
    mock_llm.call.return_value = _llm_turn(
        "request_human",
        "Of course, let me transfer you now.",
    )

    fsm = FSM(session=session, llm=mock_llm, tools=DomainToolDispatcher())
    result = await fsm.process_turn("I want to speak to a person")

    assert result.current_state == FSMState.HUMAN_HANDOFF
    assert result.session_ended is True


# ---------------------------------------------------------------------------
# Consent-refused path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_data_consent_refused_routes_to_handoff() -> None:
    """Refusing data-processing consent sends the caller to HUMAN_HANDOFF."""
    session = _make_session()
    session.current_state = FSMState.CONSENT_DATA

    mock_llm = AsyncMock()
    mock_llm.call.return_value = _llm_turn(
        "consent_refused",
        "I understand. Let me transfer you to a team member.",
    )

    fsm = FSM(session=session, llm=mock_llm, tools=DomainToolDispatcher())
    result = await fsm.process_turn("no I don't consent")

    assert result.current_state == FSMState.HUMAN_HANDOFF
    assert result.session_ended is True
    assert session.slots.data_consent_given is False


# ---------------------------------------------------------------------------
# Slot-taken retry path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slot_taken_routes_back_to_slot_search() -> None:
    """When book_appointment fails with slot_taken, FSM returns to SLOT_SEARCH."""
    session = _make_session()
    session.current_state = FSMState.BOOK
    today = date.today().isoformat()
    taken_slot_id = f"slot-{today}-0900-0"

    # Pre-book the slot so the mock will raise SlotTakenError
    talkehr_mock.reset()
    from mocks.talkehr_mock import _booked_slots
    _booked_slots.add(taken_slot_id)

    session.slots = session.slots.model_copy(update={
        "patient_id": "pat-001",
        "selected_slot_id": taken_slot_id,
        "reason_for_visit": "checkup",
        "booking_consent_given": True,
    })

    mock_llm = AsyncMock()
    mock_llm.call.return_value = _llm_turn(
        "booking_in_progress",
        "Booking now.",
        tool_call=_tc(
            ToolCallType.BOOK_APPOINTMENT,
            patient_id="pat-001",
            slot_id=taken_slot_id,
            reason="checkup",
            consent_ref="cref-test",
            idempotency_key=session.session_id,
        ),
    )

    fsm = FSM(session=session, llm=mock_llm, tools=DomainToolDispatcher())
    result = await fsm.process_turn("please book it")

    assert result.current_state == FSMState.SLOT_SEARCH
    assert session.slots.slot_taken is True
    assert session.slots.selected_slot_id is None


# ---------------------------------------------------------------------------
# Idempotent booking test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_booking_is_idempotent_on_same_session_id() -> None:
    """Booking the same session_id twice returns the same appointment."""
    talkehr_mock.reset()

    session = _make_session()
    session.current_state = FSMState.BOOK
    today = date.today().isoformat()
    slot_id = f"slot-{today}-1100-1"

    session.slots = session.slots.model_copy(update={
        "patient_id": "pat-002",
        "selected_slot_id": slot_id,
        "reason_for_visit": "follow-up",
        "booking_consent_given": True,
    })

    def _book_turn() -> LLMTurn:
        return _llm_turn(
            "booking_in_progress",
            "Booking now.",
            tool_call=_tc(
                ToolCallType.BOOK_APPOINTMENT,
                patient_id="pat-002",
                slot_id=slot_id,
                reason="follow-up",
                consent_ref="cref-idem",
                idempotency_key=session.session_id,
            ),
        )

    mock_llm = AsyncMock()
    mock_llm.call.side_effect = [_book_turn(), _book_turn()]

    fsm = FSM(session=session, llm=mock_llm, tools=DomainToolDispatcher())

    result1 = await fsm.process_turn("book it")
    appt_id_1 = session.slots.appointment_id
    code_1 = session.slots.confirmation_code

    # Reset BOOK state to force a second book call
    session.current_state = FSMState.BOOK
    session.slots = session.slots.model_copy(update={"appointment_id": None})

    result2 = await fsm.process_turn("book it again")
    appt_id_2 = session.slots.appointment_id

    # Same idempotency key → same appointment ID
    assert appt_id_1 == appt_id_2


# ---------------------------------------------------------------------------
# New-patient creation path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_patient_created_in_retrieve_or_create() -> None:
    """When IDENTIFY finds no match, RETRIEVE_OR_CREATE creates a new patient record."""
    fhir_mock.reset()

    session = _make_session()
    session.current_state = FSMState.RETRIEVE_OR_CREATE
    session.slots = session.slots.model_copy(update={
        "is_new_patient": True,
        "first_name": "Alice",
        "last_name": "Newpatient",
        "date_of_birth": "2000-03-15",
        "phone": "5559998888",
        "data_consent_given": True,
        "data_consent_ref": "cref-alice",
    })

    mock_llm = AsyncMock()
    mock_llm.call.return_value = _llm_turn(
        "creating_new",
        "I'll create your record now.",
        tool_call=_tc(
            ToolCallType.CREATE_PATIENT,
            first_name="Alice",
            last_name="Newpatient",
            date_of_birth="2000-03-15",
            phone="5559998888",
        ),
    )

    fsm = FSM(session=session, llm=mock_llm, tools=DomainToolDispatcher())
    result = await fsm.process_turn("please create my record")

    assert result.current_state == FSMState.VISIT_INTAKE
    assert session.slots.patient_id is not None
    assert session.slots.patient_id.startswith("pat-")


# ---------------------------------------------------------------------------
# Terminal states never call LLM
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("terminal_state", list(TERMINAL_STATES))
@pytest.mark.asyncio
async def test_terminal_states_return_immediately_without_llm(
    terminal_state: FSMState,
) -> None:
    session = _make_session()
    session.current_state = terminal_state

    mock_llm = AsyncMock()
    fsm = FSM(session=session, llm=mock_llm, tools=DomainToolDispatcher())

    result = await fsm.process_turn("anything")

    mock_llm.call.assert_not_called()
    assert result.session_ended is True
    assert result.current_state == terminal_state
