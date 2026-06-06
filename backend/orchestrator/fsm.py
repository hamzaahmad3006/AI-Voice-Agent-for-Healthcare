from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from models.fsm_state import (
    ConversationSession,
    FSMState,
    LLMToolCall,
    LLMTurn,
    ToolCallType,
)
from orchestrator.states import STATE_HANDLERS, StateHandler, Transition

logger = logging.getLogger(__name__)

TERMINAL_STATES: frozenset[FSMState] = frozenset(
    {FSMState.CLOSING, FSMState.HUMAN_HANDOFF, FSMState.ERROR_FALLBACK}
)


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------


class ToolResult(BaseModel):
    """Structured response from any domain tool execution."""

    model_config = ConfigDict(strict=True)

    success: bool
    # Slot names → new values to apply to session.slots.  Only bool/str/None
    # so we stay consistent with SessionSlots field types.
    slots_to_update: dict[str, str | bool | None] = {}
    error_message: str | None = None


@dataclass(frozen=True)
class FSMResult:
    response_text: str
    previous_state: FSMState
    current_state: FSMState
    transitioned: bool
    tool_executed: ToolCallType | None = None
    session_ended: bool = False


# ---------------------------------------------------------------------------
# Dependency protocols (injectable — enables unit testing without real services)
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMClientProtocol(Protocol):
    async def call(
        self,
        state_handler: StateHandler,
        transcript: str,
        session: ConversationSession,
    ) -> LLMTurn: ...


@runtime_checkable
class ToolDispatcherProtocol(Protocol):
    async def dispatch(
        self,
        tool_call: LLMToolCall,
        session: ConversationSession,
    ) -> ToolResult: ...


# ---------------------------------------------------------------------------
# FSM engine
# ---------------------------------------------------------------------------


class FSM:
    """Deterministic finite-state machine that drives one conversation session.

    The LLM is called within the bounds of each state and is only allowed to:
      - classify intent
      - extract slot values
      - generate response_text
      - assemble tool-call arguments when the state permits it

    All state transitions are evaluated by the FSM, never by the LLM.
    """

    def __init__(
        self,
        session: ConversationSession,
        llm: LLMClientProtocol,
        tools: ToolDispatcherProtocol,
    ) -> None:
        self._session = session
        self._llm = llm
        self._tools = tools

    @property
    def session(self) -> ConversationSession:
        return self._session

    async def process_turn(self, transcript: str) -> FSMResult:
        """Process one caller utterance and return the agent's response + new state."""
        previous_state = self._session.current_state
        handler = STATE_HANDLERS[previous_state]

        if handler.is_terminal:
            return FSMResult(
                response_text="",
                previous_state=previous_state,
                current_state=previous_state,
                transitioned=False,
                session_ended=True,
            )

        # 1. Call LLM within the current state's system prompt boundary.
        llm_turn = await self._llm.call(
            state_handler=handler,
            transcript=transcript,
            session=self._session,
        )

        # 2. Check for human-escalation intent (global override).
        if llm_turn.intent == "request_human":
            self._session.human_requested = True

        # 3. Apply intent-driven slot updates (e.g. consent_given → data_consent_given=True).
        self._apply_intent_slots(llm_turn.intent, handler)

        # 4. Apply LLM-extracted string slots (string fields only).
        self._apply_llm_slots(llm_turn.slots, handler)

        # 5. Execute tool call if present and permitted by this state.
        tool_executed: ToolCallType | None = None
        if llm_turn.tool_call is not None:
            if llm_turn.tool_call.name in handler.permitted_tool_calls:
                tool_executed = llm_turn.tool_call.name
                tool_result = await self._tools.dispatch(
                    llm_turn.tool_call, self._session
                )
                self._apply_tool_result(llm_turn.tool_call.name, tool_result)
            else:
                logger.warning(
                    "LLM requested disallowed tool %s in state %s — ignoring",
                    llm_turn.tool_call.name,
                    previous_state,
                )

        # 6. Global override: human-escalation wins over every state-specific transition.
        if self._session.human_requested:
            next_state = FSMState.HUMAN_HANDOFF
        else:
            next_state = self._evaluate_transitions(handler.transitions)
        transitioned = next_state != previous_state

        self._session.current_state = next_state
        self._session.turn_count += 1

        return FSMResult(
            response_text=llm_turn.response_text,
            previous_state=previous_state,
            current_state=next_state,
            transitioned=transitioned,
            tool_executed=tool_executed,
            session_ended=next_state in TERMINAL_STATES,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _apply_intent_slots(
        self, intent: str, handler: StateHandler
    ) -> None:
        updates = handler.intent_to_slots.get(intent)
        if not updates:
            return
        # model_copy preserves strict validation on the new instance.
        self._session.slots = self._session.slots.model_copy(update=updates)

    def _apply_llm_slots(
        self,
        extracted: dict[str, str | None],
        handler: StateHandler,
    ) -> None:
        """Apply string slots returned by the LLM — only allowed slots, non-null."""
        updates: dict[str, str] = {}
        for key, value in extracted.items():
            if (
                value is not None
                and key in handler.allowed_slots
                and hasattr(self._session.slots, key)
            ):
                updates[key] = value
        if updates:
            self._session.slots = self._session.slots.model_copy(update=updates)

    def _apply_tool_result(
        self, tool_name: ToolCallType, result: ToolResult
    ) -> None:
        if result.success:
            valid = {
                k: v
                for k, v in result.slots_to_update.items()
                if hasattr(self._session.slots, k)
            }
            if valid:
                self._session.slots = self._session.slots.model_copy(update=valid)
        else:
            # Handle domain-specific failure modes.
            if tool_name == ToolCallType.BOOK_APPOINTMENT:
                if result.error_message == "slot_taken":
                    self._session.slots = self._session.slots.model_copy(
                        update={"slot_taken": True, "selected_slot_id": None}
                    )
            elif tool_name == ToolCallType.CHECK_INSURANCE:
                # Insurance failure is non-blocking; mark as checked so FSM advances.
                self._session.slots = self._session.slots.model_copy(
                    update={"coverage_checked": True}
                )

    def _evaluate_transitions(self, transitions: list[Transition]) -> FSMState:
        for transition in transitions:
            if transition.guard(self._session):
                logger.debug(
                    "Transition: %s → %s (%s)",
                    self._session.current_state,
                    transition.target,
                    transition.description,
                )
                return transition.target
        return self._session.current_state
