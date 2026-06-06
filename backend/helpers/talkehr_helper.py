from __future__ import annotations

from config import settings
from models.appointment import (
    AppointmentResponse,
    BookingRequest,
    SlotSearchRequest,
    SlotSearchResponse,
)


async def search_slots(request: SlotSearchRequest) -> SlotSearchResponse:
    """Route slot search to mock or real Talkehr scheduling API."""
    if settings.use_mock_talkehr:
        from mocks import talkehr_mock
        return await talkehr_mock.search_slots(request)

    raise NotImplementedError("Real Talkehr client not yet implemented — set USE_MOCK_TALKEHR=true")


async def book_appointment(request: BookingRequest) -> AppointmentResponse:
    """Route booking to mock or real Talkehr scheduling API.

    Raises mocks.talkehr_mock.SlotTakenError when the slot is already taken.
    Callers must catch this and route FSM to SLOT_SEARCH.
    """
    if settings.use_mock_talkehr:
        from mocks import talkehr_mock
        return await talkehr_mock.book(request)

    raise NotImplementedError("Real Talkehr client not yet implemented — set USE_MOCK_TALKEHR=true")
