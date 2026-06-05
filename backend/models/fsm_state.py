from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

# Primitive values that can appear in LLM tool-call arguments (no Any)
type JsonPrimitive = str | int | float | bool | None


class FSMState(StrEnum):
    GREETING = "GREETING"
    CONSENT_DATA = "CONSENT_DATA"
    IDENTIFY = "IDENTIFY"
    RETRIEVE_OR_CREATE = "RETRIEVE_OR_CREATE"
    VISIT_INTAKE = "VISIT_INTAKE"
    SLOT_SEARCH = "SLOT_SEARCH"
    INSURANCE_CHECK = "INSURANCE_CHECK"
    CONFIRM = "CONFIRM"
    BOOK = "BOOK"
    CLOSING = "CLOSING"
    HUMAN_HANDOFF = "HUMAN_HANDOFF"
    ERROR_FALLBACK = "ERROR_FALLBACK"


class ToolCallType(StrEnum):
    LOOKUP_PATIENT = "lookup_patient"
    CREATE_PATIENT = "create_patient"
    SEARCH_SLOTS = "search_slots"
    BOOK_APPOINTMENT = "book_appointment"
    CHECK_INSURANCE = "check_insurance"
    RECORD_CONSENT = "record_consent"


class LLMToolCall(BaseModel):
    """A tool-call request produced by the LLM for the FSM to validate and execute."""

    model_config = ConfigDict(strict=True)

    name: ToolCallType
    arguments: dict[str, str | int | float | bool | None]


class LLMTurn(BaseModel):
    """Structured output contract for every LLM response.

    The orchestrator parses this JSON deterministically — no free-text scraping.
    """

    model_config = ConfigDict(strict=True)

    intent: str
    slots: dict[str, str | None]
    response_text: str
    tool_call: LLMToolCall | None = None


class SessionSlots(BaseModel):
    """All slots collectible across the full conversation.

    All optional — the FSM fills them incrementally as the call progresses.
    """

    model_config = ConfigDict(strict=True)

    # Identity
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: str | None = None  # ISO 8601 date YYYY-MM-DD
    phone: str | None = None

    # Patient resolution
    patient_id: str | None = None
    fhir_id: str | None = None
    is_new_patient: bool | None = None

    # Consent (hard gates — must be True before RETRIEVE_OR_CREATE write and BOOK)
    data_consent_given: bool | None = None
    booking_consent_given: bool | None = None
    data_consent_ref: str | None = None
    booking_consent_ref: str | None = None

    # Visit intake
    reason_for_visit: str | None = None
    location_id: str | None = None
    provider_id: str | None = None
    urgency: str | None = None
    visit_type: str | None = None

    # Scheduling
    selected_slot_id: str | None = None

    # Insurance
    insurer_name: str | None = None
    member_id: str | None = None
    group_number: str | None = None

    # Booking outcome
    appointment_id: str | None = None
    confirmation_code: str | None = None


class ConversationSession(BaseModel):
    """Live session state stored in Redis, keyed by session_id UUID."""

    model_config = ConfigDict(strict=True)

    session_id: str           # UUID — never a patient identifier
    room_name: str
    caller_number: str        # PHI — never log outside audit store
    current_state: FSMState
    slots: SessionSlots
    human_requested: bool = False
    turn_count: int = 0
    started_at: str           # ISO 8601
