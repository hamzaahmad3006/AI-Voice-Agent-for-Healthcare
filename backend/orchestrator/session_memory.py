from __future__ import annotations

import logging

import redis.asyncio as aioredis

from config import settings
from models.fsm_state import ConversationSession

logger = logging.getLogger(__name__)

# Redis key prefix — never embed PHI (caller number, patient name, etc.)
_KEY_PREFIX = "session:"


class SessionMemory:
    """Async Redis-backed session store.

    Keys: "session:<uuid>" — TTL enforced by Redis, not application code.
    Values: JSON-serialised ConversationSession (Pydantic model_dump_json).

    PHI note: the key is a UUID; the value is encrypted at the transport layer
    by Redis TLS.  No PHI appears in Redis key names.
    """

    def __init__(self) -> None:
        self._redis: aioredis.Redis = aioredis.from_url(  # type: ignore[type-arg]
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def save(self, session: ConversationSession) -> None:
        """Persist session state; refreshes the TTL on every write."""
        key = _KEY_PREFIX + session.session_id
        await self._redis.setex(
            key,
            settings.redis_session_ttl_seconds,
            session.model_dump_json(),
        )
        logger.debug("Session saved: %s (state=%s)", session.session_id, session.current_state)

    async def load(self, session_id: str) -> ConversationSession | None:
        """Return the session or None if expired / not found."""
        key = _KEY_PREFIX + session_id
        raw = await self._redis.get(key)
        if raw is None:
            logger.debug("Session not found: %s", session_id)
            return None
        try:
            return ConversationSession.model_validate_json(raw)
        except Exception as exc:
            logger.error("Failed to deserialise session %s: %s", session_id, exc)
            return None

    async def delete(self, session_id: str) -> None:
        """Remove a session (call on graceful close or timeout)."""
        key = _KEY_PREFIX + session_id
        await self._redis.delete(key)
        logger.debug("Session deleted: %s", session_id)

    async def close(self) -> None:
        """Close the Redis connection pool."""
        await self._redis.aclose()
