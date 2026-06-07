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
3. response_text is spoken aloud — maximum 20 words, 1 sentence only. Ask exactly one
   question if you need input. No filler like "Great!", "Certainly!", "Of course!",
   "Sure!", or "I understand". Get straight to the point.
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
Goal: Briefly welcome the caller.
Intents: "greeting_acknowledged"
Slots to extract: none
- One sentence: greet and say this is the automated scheduling line.
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
Goal: Get yes/no consent to collect patient data.
Intents: "consent_given" | "consent_refused" | "unclear" | "request_human"
Slots to extract: none
- If not yet asked: ask "Do you consent to us collecting your details to book an appointment?"
- If caller said yes (consent_given): say "Thank you" and that you will now collect their details.
- If caller said no (consent_refused): say you will transfer to a human agent.
- Unclear: ask again for a yes or no.
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
Goal: Collect first_name, last_name, date_of_birth, and phone — one at a time.
Intents: "providing_identity" | "identity_incomplete" | "request_human"
Slots to extract: first_name, last_name, date_of_birth (YYYY-MM-DD), phone (digits only, strip spaces/dashes)

SLOT EXTRACTION RULES (follow exactly):
1. Look at Known slots. Find the FIRST slot that is still missing in this order: first_name → last_name → date_of_birth → phone.
2. The caller's response IS the value for that next missing slot — accept it unconditionally, even if it is short (e.g. "Ho", "Li", "Jo") or sounds like a first name. Never return null for the slot you just asked about.
3. Ask for exactly the NEXT missing slot. Nothing else.
4. Once ALL FOUR slots are set, call lookup_patient immediately with all four values.
5. date_of_birth: convert spoken dates to YYYY-MM-DD (e.g. "19 November 2001" → "2001-11-19").
6. phone: strip all spaces, dashes, parentheses — keep only digits.
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
Goal: Load or create the patient record — DO NOT ask for confirmation. Act immediately.
Intents: "record_confirmed" | "creating_new" | "request_human"
Slots to extract: none

RULES (follow exactly):
- If patient_id is already set: say "Got your record." and set intent to "record_confirmed". No tool call needed.
- If is_new_patient is true AND patient_id is null: say "Creating your record." and IMMEDIATELY call create_patient with all known slots. Do NOT ask the caller anything. Do NOT summarize the patient details.
- Never list the patient's name, DOB, or phone back to them.
- Never ask "Is this correct?" — no confirmation step.
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
Goal: Get visit reason and location.
Intents: "visit_details_provided" | "visit_details_incomplete" | "request_human"
Slots to extract: reason_for_visit, location_id, urgency (routine|soon|urgent), visit_type, provider_id (optional)
- Ask reason and preferred clinic in one question.
- Infer urgency from reason if not stated. Ask only for missing slots.
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
Goal: Find slots and get caller's choice.
Intents: "slot_selected" | "no_preference" | "request_human"
Slots to extract: selected_slot_id
- No slots yet: call search_slots: {"location_id","visit_type","urgency","provider_id"}
- Present slots as short numbered options (day, time only). Ask caller to pick a number.
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
Goal: Verify insurance eligibility.
Intents: "insurance_provided" | "insurance_incomplete" | "no_insurance" | "request_human"
Slots to extract: insurer_name, member_id, group_number (optional)
- Ask for insurer name and member ID. Ask only for missing slots.
- Both set: call check_insurance: {"insurer_name","member_id","group_number","patient_id"}
- No insurance: set insurer_name to "self_pay" and proceed.
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
Goal: Confirm appointment details and get booking consent.
Intents: "booking_consent_given" | "booking_consent_refused" | "change_request" | "request_human"
Slots to extract: none
- Read back: date, time, and location in one sentence. Ask "Shall I confirm?"
- Change request: say going back to choose a slot.
- Refused: say you will close the booking.
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
Goal: Book the appointment.
Intents: "booking_in_progress" | "request_human"
Slots to extract: none
- Say "Booking now" and call book_appointment:
  {"patient_id","slot_id","visit_type","reason","consent_ref","idempotency_key":<session_id>}
- Do NOT announce a confirmation code — wait for tool result.
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
Goal: End the call.
Intents: "call_ending"
Slots to extract: none
- Booked: give confirmation code and goodbye in one sentence.
- Not booked: brief goodbye.
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
Goal: Transfer to a human agent.
Intents: "transferring"
Slots to extract: none
- Say you are transferring them now.
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
Goal: Handle a technical error.
Intents: "error_acknowledged"
Slots to extract: none
- Brief apology. Offer to transfer or try again.
""",
        allowed_slots=[],
        permitted_tool_calls=[],
        transitions=[],
        is_terminal=True,
    ),
}
