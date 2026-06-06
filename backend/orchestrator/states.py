from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from models.fsm_state import (
    ConversationSession,
    FSMState,
    ToolCallType,
)

_GLOBAL_PROMPT = """\
You are an automated healthcare appointment scheduling voice agent.

OUTPUT FORMAT — return ONLY this JSON object, no extra text:
{
  "intent": "<one of the state-specific intents listed below>",
  "slots": {"<slot_name>": "<extracted value or null>"},
  "response_text": "<what the agent says aloud>",
  "tool_call": null
}
Or, when a tool call is permitted and appropriate:
{
  "intent": "...",
  "slots": {...},
  "response_text": "...",
  "tool_call": {"name": "<tool_name>", "arguments": {"<key>": "<value>"}}
}

HARD RULES — never break these:
1. Never fabricate appointment availability, booking confirmations, or insurance data.
2. Never give medical advice or clinical interpretation.
3. response_text is spoken aloud — natural, warm, 1–3 sentences only.
4. If the caller says anything like "talk to a person", "human", "representative",
   "agent", "I want to speak to someone", or "cancel" — set intent to "request_human".
5. Extract only slots explicitly listed for this state. Do not hallucinate values.
6. If a required slot is unclear, ask for it once more in response_text.\
"""


@dataclass
class Transition:
    target: FSMState
    guard: Callable[[ConversationSession], bool]
    description: str = ""


@dataclass
class StateHandler:
    state: FSMState
    system_prompt: str
    allowed_slots: list[str]
    permitted_tool_calls: list[ToolCallType]
    transitions: list[Transition]
    # Maps specific intent values → slot updates to apply before guard evaluation.
    intent_to_slots: dict[str, dict[str, str | bool | None]] = field(
        default_factory=dict
    )
    is_terminal: bool = False


STATE_HANDLERS: dict[FSMState, StateHandler] = {
    # ------------------------------------------------------------------
    # GREETING — welcome, then immediately advance (no caller input needed)
    # ------------------------------------------------------------------
    FSMState.GREETING: StateHandler(
        state=FSMState.GREETING,
        system_prompt=_GLOBAL_PROMPT + """

STATE: GREETING
Goal: Welcome the caller warmly and introduce the automated scheduling assistant.
Intents: "greeting_acknowledged"
Slots to extract: none
- Greet naturally. Tell the caller this is an automated appointment scheduling line.
- Mention that you will need their consent before collecting any information.
""",
        allowed_slots=[],
        permitted_tool_calls=[],
        transitions=[
            Transition(
                guard=lambda s: True,
                target=FSMState.CONSENT_DATA,
                description="greeting complete — advance to consent",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # CONSENT_DATA — hard gate: must record data-processing consent
    # ------------------------------------------------------------------
    FSMState.CONSENT_DATA: StateHandler(
        state=FSMState.CONSENT_DATA,
        system_prompt=_GLOBAL_PROMPT + """

STATE: CONSENT_DATA
Goal: Obtain explicit yes/no consent for collecting and processing patient data.
Intents: "consent_given" | "consent_refused" | "unclear" | "request_human"
Slots to extract: none (consent is captured via intent only)
- Ask the caller: do they consent to having their information collected and used
  to schedule their appointment? A simple yes or no is required.
- On unclear answer, ask once more directly for a yes or no.
- On refusal, apologise and say you will transfer them to a human agent.
""",
        allowed_slots=[],
        permitted_tool_calls=[ToolCallType.RECORD_CONSENT],
        transitions=[
            Transition(
                guard=lambda s: s.human_requested,
                target=FSMState.HUMAN_HANDOFF,
                description="caller requested human",
            ),
            Transition(
                guard=lambda s: s.slots.data_consent_given is False,
                target=FSMState.HUMAN_HANDOFF,
                description="data-processing consent refused",
            ),
            Transition(
                guard=lambda s: s.slots.data_consent_given is True,
                target=FSMState.IDENTIFY,
                description="data-processing consent granted",
            ),
        ],
        intent_to_slots={
            "consent_given": {"data_consent_given": True},
            "consent_refused": {"data_consent_given": False},
        },
    ),

    # ------------------------------------------------------------------
    # IDENTIFY — collect name / DOB / phone, then call lookup_patient
    # ------------------------------------------------------------------
    FSMState.IDENTIFY: StateHandler(
        state=FSMState.IDENTIFY,
        system_prompt=_GLOBAL_PROMPT + """

STATE: IDENTIFY
Goal: Collect the caller's full name, date of birth, and phone number,
      then look them up in the patient registry.
Intents: "providing_identity" | "identity_incomplete" | "request_human"
Slots to extract: first_name, last_name, date_of_birth (ISO 8601: YYYY-MM-DD),
                  phone (digits only, no formatting)
- Ask for whichever slots are still missing.
- When all four slots are collected include a tool_call for lookup_patient.
  Arguments: {"first_name": "...", "last_name": "...", "date_of_birth": "...", "phone": "..."}
""",
        allowed_slots=["first_name", "last_name", "date_of_birth", "phone"],
        permitted_tool_calls=[ToolCallType.LOOKUP_PATIENT],
        transitions=[
            Transition(
                guard=lambda s: s.human_requested,
                target=FSMState.HUMAN_HANDOFF,
                description="caller requested human",
            ),
            Transition(
                guard=lambda s: (
                    s.slots.patient_id is not None
                    or s.slots.is_new_patient is True
                ),
                target=FSMState.RETRIEVE_OR_CREATE,
                description="identity resolved via lookup",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # RETRIEVE_OR_CREATE — load existing record or create new patient
    # ------------------------------------------------------------------
    FSMState.RETRIEVE_OR_CREATE: StateHandler(
        state=FSMState.RETRIEVE_OR_CREATE,
        system_prompt=_GLOBAL_PROMPT + """

STATE: RETRIEVE_OR_CREATE
Goal: Confirm whether the caller is an existing or new patient, then ensure
      their record exists in the system before proceeding.
Intents: "record_confirmed" | "creating_new" | "request_human"
Slots to extract: none
- For existing patients (patient_id already set): confirm their name back and proceed.
- For new patients (is_new_patient is True): explain you are creating their record,
  then include a tool_call for create_patient.
  Arguments: {"first_name": "...", "last_name": "...", "date_of_birth": "...", "phone": "..."}
""",
        allowed_slots=[],
        permitted_tool_calls=[ToolCallType.CREATE_PATIENT],
        transitions=[
            Transition(
                guard=lambda s: s.human_requested,
                target=FSMState.HUMAN_HANDOFF,
                description="caller requested human",
            ),
            Transition(
                guard=lambda s: s.slots.patient_id is not None,
                target=FSMState.VISIT_INTAKE,
                description="patient record confirmed",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # VISIT_INTAKE — collect reason, location, urgency, visit type
    # ------------------------------------------------------------------
    FSMState.VISIT_INTAKE: StateHandler(
        state=FSMState.VISIT_INTAKE,
        system_prompt=_GLOBAL_PROMPT + """

STATE: VISIT_INTAKE
Goal: Understand why the caller is coming in and capture visit details.
Intents: "visit_details_provided" | "visit_details_incomplete" | "request_human"
Slots to extract: reason_for_visit, location_id, urgency (routine | soon | urgent),
                  visit_type, provider_id (optional)
- Ask in a single natural question covering reason and preferred location.
- If urgency is not stated, infer from the reason (e.g. "chest pain" → urgent).
- location_id must be a non-empty string (ask if unknown).
""",
        allowed_slots=[
            "reason_for_visit",
            "location_id",
            "urgency",
            "visit_type",
            "provider_id",
        ],
        permitted_tool_calls=[],
        transitions=[
            Transition(
                guard=lambda s: s.human_requested,
                target=FSMState.HUMAN_HANDOFF,
                description="caller requested human",
            ),
            Transition(
                guard=lambda s: (
                    s.slots.reason_for_visit is not None
                    and s.slots.location_id is not None
                ),
                target=FSMState.SLOT_SEARCH,
                description="visit details collected",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # SLOT_SEARCH — fetch available slots, present them, capture selection
    # ------------------------------------------------------------------
    FSMState.SLOT_SEARCH: StateHandler(
        state=FSMState.SLOT_SEARCH,
        system_prompt=_GLOBAL_PROMPT + """

STATE: SLOT_SEARCH
Goal: Find available appointment slots and let the caller choose one.
Intents: "slot_selected" | "no_preference" | "request_human"
Slots to extract: selected_slot_id
- If no slots have been fetched yet (selected_slot_id is null), call search_slots.
  Arguments: {"location_id": "...", "visit_type": "...", "urgency": "...",
              "provider_id": "<if known or null>"}
- After presenting slots read them out as numbered options and ask the caller
  to choose. Extract selected_slot_id from their spoken choice.
""",
        allowed_slots=["selected_slot_id"],
        permitted_tool_calls=[ToolCallType.SEARCH_SLOTS],
        transitions=[
            Transition(
                guard=lambda s: s.human_requested,
                target=FSMState.HUMAN_HANDOFF,
                description="caller requested human",
            ),
            Transition(
                guard=lambda s: s.slots.selected_slot_id is not None,
                target=FSMState.INSURANCE_CHECK,
                description="slot selected",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # INSURANCE_CHECK — collect insurance details and verify eligibility
    # ------------------------------------------------------------------
    FSMState.INSURANCE_CHECK: StateHandler(
        state=FSMState.INSURANCE_CHECK,
        system_prompt=_GLOBAL_PROMPT + """

STATE: INSURANCE_CHECK
Goal: Collect insurance details and verify the caller's eligibility.
Intents: "insurance_provided" | "insurance_incomplete" | "no_insurance" | "request_human"
Slots to extract: insurer_name, member_id, group_number (optional)
- Ask the caller for their insurance provider, member ID, and group number.
- When insurer_name and member_id are both set, call check_insurance.
  Arguments: {"insurer_name": "...", "member_id": "...",
              "group_number": "<if known or null>", "patient_id": "..."}
- On "no_insurance" intent, set insurer_name to "self_pay" and proceed.
""",
        allowed_slots=["insurer_name", "member_id", "group_number"],
        permitted_tool_calls=[ToolCallType.CHECK_INSURANCE],
        intent_to_slots={
            "no_insurance": {"insurer_name": "self_pay"},
        },
        transitions=[
            Transition(
                guard=lambda s: s.human_requested,
                target=FSMState.HUMAN_HANDOFF,
                description="caller requested human",
            ),
            Transition(
                guard=lambda s: s.slots.coverage_checked,
                target=FSMState.CONFIRM,
                description="insurance check complete",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # CONFIRM — summarise booking and obtain booking consent
    # ------------------------------------------------------------------
    FSMState.CONFIRM: StateHandler(
        state=FSMState.CONFIRM,
        system_prompt=_GLOBAL_PROMPT + """

STATE: CONFIRM
Goal: Read the full appointment summary back to the caller and obtain their
      verbal consent to proceed with the booking.
Intents: "booking_consent_given" | "booking_consent_refused" | "change_request" | "request_human"
Slots to extract: none (consent captured via intent; change_request via intent)
- Summarise: date, time, provider, location, and reason.
- Ask: "Do you confirm this appointment? Please say yes or no."
- On "change_request": acknowledge and say you will go back to choose a different slot.
- On "booking_consent_refused": apologise and offer to end the call or transfer.
""",
        allowed_slots=[],
        permitted_tool_calls=[ToolCallType.RECORD_CONSENT],
        intent_to_slots={
            "booking_consent_given": {"booking_consent_given": True},
            "booking_consent_refused": {"booking_consent_given": False},
            "change_request": {"change_requested": True},
        },
        transitions=[
            Transition(
                guard=lambda s: s.human_requested,
                target=FSMState.HUMAN_HANDOFF,
                description="caller requested human",
            ),
            Transition(
                guard=lambda s: s.slots.change_requested,
                target=FSMState.SLOT_SEARCH,
                description="caller wants a different slot",
            ),
            Transition(
                guard=lambda s: s.slots.booking_consent_given is False,
                target=FSMState.CLOSING,
                description="booking consent refused — close without booking",
            ),
            Transition(
                guard=lambda s: s.slots.booking_consent_given is True,
                target=FSMState.BOOK,
                description="booking consent granted",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # BOOK — execute the booking tool call
    # ------------------------------------------------------------------
    FSMState.BOOK: StateHandler(
        state=FSMState.BOOK,
        system_prompt=_GLOBAL_PROMPT + """

STATE: BOOK
Goal: Finalise the appointment booking.
Intents: "booking_in_progress" | "request_human"
Slots to extract: none
- Call book_appointment with all required arguments.
  Arguments: {"patient_id": "...", "slot_id": "...", "visit_type": "...",
              "reason": "...", "consent_ref": "...", "idempotency_key": "<session_id>"}
- Tell the caller you are confirming their appointment now.
- Do NOT announce a confirmation code — that comes from the tool result.
""",
        allowed_slots=[],
        permitted_tool_calls=[ToolCallType.BOOK_APPOINTMENT],
        transitions=[
            Transition(
                guard=lambda s: s.human_requested,
                target=FSMState.HUMAN_HANDOFF,
                description="caller requested human",
            ),
            Transition(
                guard=lambda s: s.slots.slot_taken,
                target=FSMState.SLOT_SEARCH,
                description="selected slot was taken — re-fetch available slots",
            ),
            Transition(
                guard=lambda s: s.slots.appointment_id is not None,
                target=FSMState.CLOSING,
                description="booking confirmed",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # CLOSING — confirm booking and end the call gracefully
    # ------------------------------------------------------------------
    FSMState.CLOSING: StateHandler(
        state=FSMState.CLOSING,
        system_prompt=_GLOBAL_PROMPT + """

STATE: CLOSING
Goal: Thank the caller and provide the confirmation code if a booking was made.
Intents: "call_ending"
Slots to extract: none
- If appointment_id is set: read the confirmation code and say goodbye.
- If no booking was made: thank the caller and say goodbye.
""",
        allowed_slots=[],
        permitted_tool_calls=[],
        transitions=[],
        is_terminal=True,
    ),

    # ------------------------------------------------------------------
    # HUMAN_HANDOFF — warm transfer to a human agent
    # ------------------------------------------------------------------
    FSMState.HUMAN_HANDOFF: StateHandler(
        state=FSMState.HUMAN_HANDOFF,
        system_prompt=_GLOBAL_PROMPT + """

STATE: HUMAN_HANDOFF
Goal: Transfer the caller to a human agent.
Intents: "transferring"
Slots to extract: none
- Acknowledge the request warmly.
- Say you are transferring them now and thank them for their patience.
""",
        allowed_slots=[],
        permitted_tool_calls=[],
        transitions=[],
        is_terminal=True,
    ),

    # ------------------------------------------------------------------
    # ERROR_FALLBACK — graceful recovery from unrecoverable service failure
    # ------------------------------------------------------------------
    FSMState.ERROR_FALLBACK: StateHandler(
        state=FSMState.ERROR_FALLBACK,
        system_prompt=_GLOBAL_PROMPT + """

STATE: ERROR_FALLBACK
Goal: Apologise for the technical issue and offer next steps.
Intents: "error_acknowledged"
Slots to extract: none
- Apologise briefly for the technical difficulty.
- Offer to transfer to a human agent or ask the caller to try again later.
""",
        allowed_slots=[],
        permitted_tool_calls=[],
        transitions=[],
        is_terminal=True,
    ),
}
