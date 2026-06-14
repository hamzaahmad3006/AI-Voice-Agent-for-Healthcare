from __future__ import annotations

import json
import logging

from groq import AsyncGroq
from groq import APIError, APITimeoutError

from config import settings
from models.fsm_state import ConversationSession, LLMTurn
from orchestrator.states import StateHandler

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_TIMEOUT_SECONDS = 10.0


class GroqLLMClient:
    """Calls the Groq API with a per-state system prompt and enforces JSON output.

    Conforms to LLMClientProtocol (duck-typed — no import needed to avoid
    circular references between fsm.py and this module).
    """

    def __init__(self) -> None:
        self._client = AsyncGroq(
            api_key=settings.groq_api_key,
            timeout=_TIMEOUT_SECONDS,
            max_retries=_MAX_RETRIES,
        )

    async def call(
        self,
        state_handler: StateHandler,
        transcript: str,
        session: ConversationSession,
    ) -> LLMTurn:
        """Send one turn to Groq and parse the structured response.

        Raises ValueError if the model returns malformed JSON that cannot be
        coerced into LLMTurn — the FSM treats this as an ERROR_FALLBACK trigger.
        """
        system_prompt = self._build_system_prompt(state_handler, session)

        try:
            completion = await self._client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=400,
            )
        except APITimeoutError as exc:
            logger.error("Groq timeout in state %s: %s", state_handler.state, exc)
            raise
        except APIError as exc:
            logger.error("Groq API error in state %s: %s", state_handler.state, exc)
            raise

        raw = completion.choices[0].message.content or "{}"

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error(
                "Groq returned non-JSON in state %s: %r", state_handler.state, raw
            )
            raise ValueError(f"LLM returned non-JSON: {raw!r}") from exc

        # Coerce into the strict LLMTurn contract.
        try:
            return LLMTurn.model_validate(data)
        except Exception as exc:
            logger.error(
                "LLMTurn validation failed in state %s: %s — raw: %r",
                state_handler.state,
                exc,
                data,
            )
            raise ValueError(f"LLM response failed schema validation: {exc}") from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_system_prompt(
        self, handler: StateHandler, session: ConversationSession
    ) -> str:
        """Inject minimal, per-state session context below the state prompt."""
        ctx_lines: list[str] = [
            f"Current state: {session.current_state}",
            f"Turn number: {session.turn_count + 1}",
        ]

        slots = session.slots
        # Surface only the slots that are already known and relevant to this state
        # so the LLM can reference them in its response without PHI leaking elsewhere.
        known: dict[str, str | bool | None] = {}
        for name in handler.allowed_slots:
            val = getattr(slots, name, None)
            if val is not None:
                known[name] = val
        if known:
            ctx_lines.append(f"Known slots: {json.dumps(known)}")

        # Inject available slots for SLOT_SEARCH so LLM can present options.
        if slots.available_slots_json:
            ctx_lines.append(f"Available slots (JSON): {slots.available_slots_json}")

        ctx_block = "\n".join(ctx_lines)
        return f"{handler.system_prompt}\n\nSESSION CONTEXT:\n{ctx_block}"
