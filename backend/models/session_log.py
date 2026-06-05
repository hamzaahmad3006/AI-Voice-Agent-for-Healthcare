from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from models.fsm_state import FSMState


class ConsentType(StrEnum):
    DATA_PROCESSING = "data_processing"
    BOOKING = "booking"


class ConsentValue(StrEnum):
    YES = "yes"
    NO = "no"
    UNCLEAR = "unclear"


class SessionOutcome(StrEnum):
    BOOKED = "booked"
    NO_BOOKING = "no_booking"
    TRANSFERRED = "transferred"
    ERROR = "error"


class ConsentEvent(BaseModel):
    """Immutable consent record — never modified after creation."""

    model_config = ConfigDict(strict=True)

    type: ConsentType
    value: ConsentValue
    at: str                     # ISO 8601
    transcript_snippet: str     # verbatim caller words — PHI
    session_id: str


class TurnLog(BaseModel):
    model_config = ConfigDict(strict=True)

    n: int
    state: FSMState
    agent_text: str
    caller_text: str | None = None
    latency_ms: int | None = None


class ToolCallLog(BaseModel):
    model_config = ConfigDict(strict=True)

    tool: str
    status: str             # "ok" | "error" | "timeout"
    latency_ms: int
    error_message: str | None = None


class SessionLog(BaseModel):
    """Append-only, encrypted audit record for a single call session.

    PHI fields are tagged in phi_tags — they must never appear in
    operational logs, metrics, or trace spans.
    """

    model_config = ConfigDict(strict=True)

    session_id: str
    room_name: str
    caller_number: str          # PHI
    patient_id: str | None = None  # PHI
    started_at: str             # ISO 8601
    ended_at: str | None = None # ISO 8601
    outcome: SessionOutcome | None = None
    final_state: FSMState
    consent_events: list[ConsentEvent] = []
    turns: list[TurnLog] = []
    tool_calls: list[ToolCallLog] = []
    phi_tags: list[str] = ["caller_number", "patient_id"]
