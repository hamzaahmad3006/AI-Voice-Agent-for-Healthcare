from __future__ import annotations

import uuid
from datetime import datetime, timezone

from models.session_log import ConsentEvent, ConsentType, ConsentValue


async def record_consent(
    session_id: str,
    consent_type: ConsentType,
    value: ConsentValue,
    transcript_snippet: str,
) -> ConsentEvent:
    """Create an immutable consent record and return it.

    In MVP this is in-process only. Production implementation would persist
    to the append-only audit store (AES-256 encrypted, PHI-tagged).
    """
    event = ConsentEvent(
        type=consent_type,
        value=value,
        at=datetime.now(timezone.utc).isoformat(),
        transcript_snippet=transcript_snippet,
        session_id=session_id,
    )
    # Consent records are immutable once written — no update or delete path.
    return event


def new_consent_ref() -> str:
    """Generate a unique, opaque reference ID for a consent record."""
    return f"cref-{uuid.uuid4().hex}"
