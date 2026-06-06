"""LiveKit Agent worker — entry point for the voice agent process.

One worker process handles multiple concurrent calls.  Each inbound call
gets its own asyncio task, its own FsmAdapter, and its own ConversationSession.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 LOCAL DEV SETUP (localhost LiveKit)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Start the LiveKit server (Docker):

       docker run --rm \\
         -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \\
         livekit/livekit-server --dev

   Dev mode defaults:
       URL     : ws://localhost:7880
       API key : devkey
       Secret  : secret

2. Set backend/.env:

       LIVEKIT_URL=ws://localhost:7880
       LIVEKIT_API_KEY=devkey
       LIVEKIT_API_SECRET=secret

3. Start the worker (from backend/ directory):

       python -m agent.worker dev

4. Join a room via the LiveKit Playground or a test client.
   The agent will answer and start the appointment booking flow.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import asyncio
import logging

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli

from agent.pipeline import FsmAdapter, GREETING_TEXT, build_voice_assistant, new_session
from config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


async def entrypoint(ctx: JobContext) -> None:
    """Called once per inbound call — runs for the lifetime of that call."""

    logger.info("Call received  room=%s", ctx.room.name)

    # ── 1. Connect to the LiveKit room (audio only — no video needed) ──────
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # ── 2. Build session + FSM adapter ────────────────────────────────────
    session = new_session(ctx)
    adapter = FsmAdapter(session)

    logger.info(
        "Session created  session_id=%s  room=%s",
        session.session_id,
        ctx.room.name,
    )

    # ── 3. Build and start the voice pipeline ─────────────────────────────
    assistant = build_voice_assistant(adapter)
    assistant.start(ctx.room)

    # ── 4. Wait for the caller to join, then deliver the opening greeting ──
    await ctx.wait_for_participant()
    logger.info("Caller joined  room=%s", ctx.room.name)

    await assistant.say(GREETING_TEXT, allow_interruptions=False)

    # ── 5. Run until FSM reaches a terminal state ──────────────────────────
    # adapter.session_ended fires when FSM enters CLOSING / HUMAN_HANDOFF /
    # ERROR_FALLBACK.  We also guard against the participant leaving early.
    done, pending = await asyncio.wait(
        [
            asyncio.create_task(adapter.session_ended.wait(), name="session_ended"),
            asyncio.create_task(_wait_for_disconnect(ctx), name="participant_left"),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    # ── 6. Cleanup ─────────────────────────────────────────────────────────
    final_state = adapter.fsm.session.current_state
    logger.info(
        "Call ended  session_id=%s  final_state=%s",
        session.session_id,
        final_state,
    )

    await adapter.cleanup()
    await assistant.aclose()


async def _wait_for_disconnect(ctx: JobContext) -> None:
    """Resolve when all non-agent participants have left the room."""
    while True:
        participants = [
            p for p in ctx.room.remote_participants.values()
            if not p.identity.startswith("agent-")
        ]
        if not participants:
            await asyncio.sleep(0.5)
            continue
        # At least one caller is present — wait for them to leave.
        break

    while True:
        callers = [
            p for p in ctx.room.remote_participants.values()
            if not p.identity.startswith("agent-")
        ]
        if not callers:
            return
        await asyncio.sleep(1.0)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # URL / key / secret are loaded from LIVEKIT_URL, LIVEKIT_API_KEY,
            # LIVEKIT_API_SECRET environment variables by the SDK automatically.
        )
    )
