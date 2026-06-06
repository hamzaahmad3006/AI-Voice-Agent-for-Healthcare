from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, Response

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

log = structlog.get_logger()

# LiveKit event types we handle explicitly; all others are silently ignored.
_TRACKED_EVENTS: frozenset[str] = frozenset(
    {"room_started", "room_finished", "participant_joined", "participant_left"}
)


@router.post("/livekit", status_code=204)
async def livekit_webhook(request: Request) -> Response:
    """Receive LiveKit room lifecycle events.

    Production hardening (next step): verify the Authorization JWT using
    LIVEKIT_API_SECRET before processing.  For MVP the event is logged and
    acknowledged immediately.

    PHI note: room names are UUID-based — never patient names or phone numbers.
    """
    body: dict[str, object] = await request.json()
    event_type = str(body.get("event", ""))

    if event_type in _TRACKED_EVENTS:
        room = body.get("room", {})
        room_name = room.get("name", "") if isinstance(room, dict) else ""
        log.info("livekit_webhook", event=event_type, room=room_name)

    return Response(status_code=204)
