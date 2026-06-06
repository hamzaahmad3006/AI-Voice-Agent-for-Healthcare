"""Unit tests for mock service implementations.

All tests are pure in-memory — no network, no Redis, no real FHIR/Talkehr.
"""
from __future__ import annotations

import pytest

from mocks import fhir_mock, insurance_mock, talkehr_mock
from models.appointment import BookingRequest, SlotSearchRequest
from models.insurance import EligibilityStatus, InsuranceCheckRequest
from models.patient import (
    PatientCreateRequest,
    PatientLookupRequest,
    PatientMatchStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_mocks() -> None:
    """Reset all mock stores before each test."""
    fhir_mock.reset()
    talkehr_mock.reset()


# ---------------------------------------------------------------------------
# FHIR mock — lookup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fhir_lookup_existing_patient_by_exact_match() -> None:
    req = PatientLookupRequest(
        first_name="Sarah",
        last_name="Johnson",
        date_of_birth="1985-04-12",
        phone="5550001001",
    )
    resp = await fhir_mock.lookup(req)

    assert resp.status == PatientMatchStatus.EXISTING_PATIENT
    assert resp.patient is not None
    assert resp.patient.patient_id == "pat-001"
    assert resp.patient.first_name == "Sarah"


@pytest.mark.asyncio
async def test_fhir_lookup_fuzzy_name_match() -> None:
    # Slight STT noise: "Saraa" instead of "Sarah"
    req = PatientLookupRequest(
        first_name="Saraa",
        last_name="Johnson",
        date_of_birth="1985-04-12",
        phone="5550001001",
    )
    resp = await fhir_mock.lookup(req)

    assert resp.status == PatientMatchStatus.EXISTING_PATIENT
    assert resp.patient is not None
    assert resp.patient.patient_id == "pat-001"


@pytest.mark.asyncio
async def test_fhir_lookup_no_match_returns_no_match() -> None:
    req = PatientLookupRequest(
        first_name="Unknown",
        last_name="Person",
        date_of_birth="2000-01-01",
        phone="0000000000",
    )
    resp = await fhir_mock.lookup(req)

    assert resp.status == PatientMatchStatus.NO_MATCH
    assert resp.patient is None
    assert resp.candidates == []


@pytest.mark.asyncio
async def test_fhir_lookup_phone_with_formatting_is_normalised() -> None:
    req = PatientLookupRequest(
        first_name="Sarah",
        last_name="Johnson",
        date_of_birth="1985-04-12",
        phone="(555) 000-1001",
    )
    resp = await fhir_mock.lookup(req)

    assert resp.status == PatientMatchStatus.EXISTING_PATIENT


# ---------------------------------------------------------------------------
# FHIR mock — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fhir_create_returns_new_patient_id() -> None:
    req = PatientCreateRequest(
        first_name="New",
        last_name="Patient",
        date_of_birth="1999-06-15",
        phone="5559990000",
        consent_ref="cref-test-001",
    )
    resp = await fhir_mock.create(req)

    assert resp.patient_id.startswith("pat-")
    assert resp.fhir_id.startswith("fhir-")
    assert resp.created is True
    assert resp.created_at


@pytest.mark.asyncio
async def test_fhir_create_then_lookup_finds_new_patient() -> None:
    create_req = PatientCreateRequest(
        first_name="Brand",
        last_name="New",
        date_of_birth="1995-03-20",
        phone="5558880000",
        consent_ref="cref-test-002",
    )
    create_resp = await fhir_mock.create(create_req)

    lookup_req = PatientLookupRequest(
        first_name="Brand",
        last_name="New",
        date_of_birth="1995-03-20",
        phone="5558880000",
    )
    lookup_resp = await fhir_mock.lookup(lookup_req)

    assert lookup_resp.status == PatientMatchStatus.EXISTING_PATIENT
    assert lookup_resp.patient is not None
    assert lookup_resp.patient.patient_id == create_resp.patient_id


# ---------------------------------------------------------------------------
# Talkehr mock — search slots
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_talkehr_search_returns_slots() -> None:
    req = SlotSearchRequest(
        location_id="loc-downtown",
        visit_type="consult",
        from_date="2026-06-10",
        to_date="2026-06-24",
    )
    resp = await talkehr_mock.search_slots(req)

    assert len(resp.slots) > 0
    for slot in resp.slots:
        assert slot.slot_id
        assert slot.start
        assert slot.end
        assert slot.location_id == "loc-downtown"


# ---------------------------------------------------------------------------
# Talkehr mock — book appointment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_talkehr_book_returns_confirmation() -> None:
    # First get a slot
    search_req = SlotSearchRequest(
        location_id="loc-downtown",
        visit_type="consult",
        from_date="2026-06-10",
        to_date="2026-06-24",
    )
    search_resp = await talkehr_mock.search_slots(search_req)
    slot_id = search_resp.slots[0].slot_id

    book_req = BookingRequest(
        patient_id="pat-001",
        slot_id=slot_id,
        reason="Annual checkup",
        consent_ref="cref-booking-001",
        idempotency_key="session-abc-001",
    )
    appt = await talkehr_mock.book(book_req)

    assert appt.appointment_id.startswith("appt-")
    assert appt.confirmation_code.startswith("CONF-")
    assert appt.patient_id == "pat-001"
    assert appt.slot_id == slot_id


@pytest.mark.asyncio
async def test_talkehr_book_is_idempotent() -> None:
    search_req = SlotSearchRequest(
        location_id="loc-downtown",
        visit_type="consult",
        from_date="2026-06-10",
        to_date="2026-06-24",
    )
    search_resp = await talkehr_mock.search_slots(search_req)
    slot_id = search_resp.slots[0].slot_id

    book_req = BookingRequest(
        patient_id="pat-001",
        slot_id=slot_id,
        reason="Checkup",
        consent_ref="cref-001",
        idempotency_key="idem-key-999",
    )
    first = await talkehr_mock.book(book_req)
    second = await talkehr_mock.book(book_req)

    assert first.appointment_id == second.appointment_id
    assert first.confirmation_code == second.confirmation_code


@pytest.mark.asyncio
async def test_talkehr_book_raises_slot_taken_on_double_book() -> None:
    search_req = SlotSearchRequest(
        location_id="loc-downtown",
        visit_type="consult",
        from_date="2026-06-10",
        to_date="2026-06-24",
    )
    search_resp = await talkehr_mock.search_slots(search_req)
    slot_id = search_resp.slots[0].slot_id

    await talkehr_mock.book(BookingRequest(
        patient_id="pat-001",
        slot_id=slot_id,
        reason="First",
        consent_ref="cref-a",
        idempotency_key="idem-a",
    ))

    with pytest.raises(talkehr_mock.SlotTakenError):
        await talkehr_mock.book(BookingRequest(
            patient_id="pat-002",
            slot_id=slot_id,
            reason="Second",
            consent_ref="cref-b",
            idempotency_key="idem-b",  # different key → not idempotent
        ))


# ---------------------------------------------------------------------------
# Insurance mock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insurance_known_payer_is_eligible() -> None:
    req = InsuranceCheckRequest(
        payer_name="BlueCross",
        member_id="MBR-001",
        patient_dob="1985-04-12",
        provider_id="prov-001",
    )
    resp = await insurance_mock.check(req)

    assert resp.eligibility == EligibilityStatus.ELIGIBLE
    assert resp.in_network is True


@pytest.mark.asyncio
async def test_insurance_self_pay_is_eligible() -> None:
    req = InsuranceCheckRequest(
        payer_name="self_pay",
        member_id="N/A",
        patient_dob="1985-04-12",
        provider_id="prov-001",
    )
    resp = await insurance_mock.check(req)

    assert resp.eligibility == EligibilityStatus.ELIGIBLE
    assert resp.plan_name == "Self Pay"


@pytest.mark.asyncio
async def test_insurance_unknown_payer_requires_staff_verification() -> None:
    req = InsuranceCheckRequest(
        payer_name="ObscurePlan2000",
        member_id="MBR-XYZ",
        patient_dob="1985-04-12",
        provider_id="prov-001",
    )
    resp = await insurance_mock.check(req)

    assert resp.eligibility == EligibilityStatus.UNKNOWN
    assert resp.requires_staff_verification is True


@pytest.mark.asyncio
async def test_insurance_bad_member_id_prefix_returns_unknown() -> None:
    req = InsuranceCheckRequest(
        payer_name="Aetna",
        member_id="UNK-12345",
        patient_dob="1985-04-12",
        provider_id="prov-001",
    )
    resp = await insurance_mock.check(req)

    assert resp.eligibility == EligibilityStatus.UNKNOWN
