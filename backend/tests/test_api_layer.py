"""Tests for Phase 5 — FastAPI routes and controllers.

Strategy:
- Use FastAPI's TestClient (sync starlette wrapper) for route tests.
- Patch controller functions so tests need no Redis, no database.
- Controller unit tests run in isolation with mocked SessionMemory.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from models.appointment import AppointmentStatus, AppointmentSummary
from models.fsm_state import ConversationSession, FSMState, SessionSlots
from models.patient import PatientMatchStatus, PatientRecord
from models.session_log import SessionListItem, SessionLog, SessionOutcome

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(state: FSMState = FSMState.CONSENT_DATA) -> ConversationSession:
    return ConversationSession(
        session_id=str(uuid.uuid4()),
        room_name="test-room",
        caller_number="5550001234",
        current_state=state,
        slots=SessionSlots(),
        started_at="2026-06-06T10:00:00Z",
    )


def _make_session_with_booking(session_id: str | None = None) -> ConversationSession:
    sid = session_id or str(uuid.uuid4())
    slots = SessionSlots(
        patient_id="pat-001",
        appointment_id="appt-abc123",
        confirmation_code="CONF-XYZ",
        selected_slot_id="slot-001",
    )
    return ConversationSession(
        session_id=sid,
        room_name="test-room",
        caller_number="5550001234",
        current_state=FSMState.CLOSING,
        slots=slots,
        started_at="2026-06-06T10:00:00Z",
    )


def _make_session_list_item(session: ConversationSession) -> SessionListItem:
    return SessionListItem(
        session_id=session.session_id,
        started_at=session.started_at,
        ended_at=None,
        outcome=None,
        final_state=session.current_state,
        patient_id=session.slots.patient_id,
    )


def _make_session_log(session: ConversationSession) -> SessionLog:
    return SessionLog(
        session_id=session.session_id,
        room_name=session.room_name,
        caller_number=session.caller_number,
        patient_id=session.slots.patient_id,
        started_at=session.started_at,
        ended_at=None,
        outcome=None,
        final_state=session.current_state,
    )


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health_ok_when_redis_unreachable() -> None:
    """Health route is always reachable; redis status is 'unreachable' when Redis is down."""
    with patch("routes.health._ping_redis", new_callable=AsyncMock, return_value="unreachable"):
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["redis"] == "unreachable"
    assert "environment" in data


def test_health_ok_when_redis_up() -> None:
    with patch("routes.health._ping_redis", new_callable=AsyncMock, return_value="ok"):
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["redis"] == "ok"


# ---------------------------------------------------------------------------
# GET /sessions
# ---------------------------------------------------------------------------


def test_list_sessions_returns_empty_list() -> None:
    with patch(
        "routes.sessions.get_active_sessions",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = client.get("/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_sessions_returns_items() -> None:
    session = _make_session()
    item = _make_session_list_item(session)
    with patch(
        "routes.sessions.get_active_sessions",
        new_callable=AsyncMock,
        return_value=[item],
    ):
        resp = client.get("/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["session_id"] == session.session_id
    assert body[0]["final_state"] == FSMState.CONSENT_DATA


# ---------------------------------------------------------------------------
# GET /sessions/{session_id}
# ---------------------------------------------------------------------------


def test_get_session_returns_404_when_not_found() -> None:
    with patch(
        "routes.sessions.get_session_detail",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = client.get(f"/sessions/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_session_returns_log() -> None:
    session = _make_session(FSMState.SLOT_SEARCH)
    log = _make_session_log(session)
    with patch(
        "routes.sessions.get_session_detail",
        new_callable=AsyncMock,
        return_value=log,
    ):
        resp = client.get(f"/sessions/{session.session_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session.session_id
    assert data["final_state"] == FSMState.SLOT_SEARCH


# ---------------------------------------------------------------------------
# POST /webhooks/livekit
# ---------------------------------------------------------------------------


def test_livekit_webhook_room_started() -> None:
    payload = {"event": "room_started", "room": {"name": "room-abc123"}}
    resp = client.post("/webhooks/livekit", json=payload)
    assert resp.status_code == 204


def test_livekit_webhook_participant_joined() -> None:
    payload = {
        "event": "participant_joined",
        "room": {"name": "room-xyz"},
        "participant": {"identity": "caller-001"},
    }
    resp = client.post("/webhooks/livekit", json=payload)
    assert resp.status_code == 204


def test_livekit_webhook_unknown_event_ignored() -> None:
    payload = {"event": "some_unknown_event", "room": {"name": "room-xyz"}}
    resp = client.post("/webhooks/livekit", json=payload)
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# session_controller unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_controller_get_active_sessions() -> None:
    from controllers.session_controller import get_active_sessions

    session = _make_session()
    mock_memory = MagicMock()
    mock_memory.list_all = AsyncMock(return_value=[session])

    with patch("controllers.session_controller._memory", mock_memory):
        result = await get_active_sessions()

    assert len(result) == 1
    assert result[0].session_id == session.session_id
    assert result[0].final_state == FSMState.CONSENT_DATA


@pytest.mark.asyncio
async def test_session_controller_get_detail_returns_none_when_missing() -> None:
    from controllers.session_controller import get_session_detail

    mock_memory = MagicMock()
    mock_memory.load = AsyncMock(return_value=None)

    with patch("controllers.session_controller._memory", mock_memory):
        result = await get_session_detail("nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_session_controller_get_detail_maps_session() -> None:
    from controllers.session_controller import get_session_detail

    session = _make_session(FSMState.IDENTIFY)
    mock_memory = MagicMock()
    mock_memory.load = AsyncMock(return_value=session)

    with patch("controllers.session_controller._memory", mock_memory):
        result = await get_session_detail(session.session_id)

    assert result is not None
    assert result.session_id == session.session_id
    assert result.final_state == FSMState.IDENTIFY


# ---------------------------------------------------------------------------
# booking_controller unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_booking_controller_returns_none_when_session_missing() -> None:
    from controllers.booking_controller import get_booking_status

    mock_memory = MagicMock()
    mock_memory.load = AsyncMock(return_value=None)

    with patch("controllers.booking_controller._memory", mock_memory):
        result = await get_booking_status("missing-session")

    assert result is None


@pytest.mark.asyncio
async def test_booking_controller_returns_none_when_no_appointment() -> None:
    from controllers.booking_controller import get_booking_status

    session = _make_session()  # no appointment_id
    mock_memory = MagicMock()
    mock_memory.load = AsyncMock(return_value=session)

    with patch("controllers.booking_controller._memory", mock_memory):
        result = await get_booking_status(session.session_id)

    assert result is None


@pytest.mark.asyncio
async def test_booking_controller_returns_summary() -> None:
    from controllers.booking_controller import get_booking_status

    session = _make_session_with_booking()
    mock_memory = MagicMock()
    mock_memory.load = AsyncMock(return_value=session)

    with patch("controllers.booking_controller._memory", mock_memory):
        result = await get_booking_status(session.session_id)

    assert result is not None
    assert result.appointment_id == "appt-abc123"
    assert result.confirmation_code == "CONF-XYZ"
    assert result.status == AppointmentStatus.BOOKED


# ---------------------------------------------------------------------------
# patient_controller unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patient_controller_returns_none_when_session_missing() -> None:
    from controllers.patient_controller import get_patient_for_session

    mock_memory = MagicMock()
    mock_memory.load = AsyncMock(return_value=None)

    with patch("controllers.patient_controller._memory", mock_memory):
        result = await get_patient_for_session("missing")

    assert result is None


@pytest.mark.asyncio
async def test_patient_controller_returns_none_when_no_patient_id() -> None:
    from controllers.patient_controller import get_patient_for_session

    session = _make_session()  # no patient_id
    mock_memory = MagicMock()
    mock_memory.load = AsyncMock(return_value=session)

    with patch("controllers.patient_controller._memory", mock_memory):
        result = await get_patient_for_session(session.session_id)

    assert result is None




@pytest.mark.asyncio
async def test_patient_controller_fhir_mock_direct() -> None:
    """Patient controller returns PatientRecord by delegating to get_patient_by_id."""
    from controllers.patient_controller import get_patient_for_session

    session_id = str(uuid.uuid4())
    session = ConversationSession(
        session_id=session_id,
        room_name="room",
        caller_number="5550001234",
        current_state=FSMState.CLOSING,
        slots=SessionSlots(patient_id="pat-001"),
        started_at="2026-06-06T10:00:00Z",
    )
    mock_record = PatientRecord(
        patient_id="pat-001",
        fhir_id="fhir-001",
        first_name="Sarah",
        last_name="Johnson",
        dob="1985-03-15",
        phone="5550001111",
        is_new=False,
        created_at="2026-01-01T00:00:00Z",
    )

    mock_memory = MagicMock()
    mock_memory.load = AsyncMock(return_value=session)

    with (
        patch("controllers.patient_controller._memory", mock_memory),
        patch(
            "controllers.patient_controller.get_patient_by_id",
            new_callable=AsyncMock,
            return_value=mock_record,
        ),
    ):
        result = await get_patient_for_session(session_id)

    assert result is not None
    assert result.patient_id == "pat-001"
    assert result.first_name == "Sarah"
