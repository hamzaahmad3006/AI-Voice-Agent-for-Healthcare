from __future__ import annotations

from config import settings
from models.patient import (
    PatientCreateRequest,
    PatientCreateResponse,
    PatientLookupRequest,
    PatientLookupResponse,
)


async def lookup_patient(request: PatientLookupRequest) -> PatientLookupResponse:
    """Route patient lookup to mock or real FHIR R4 server."""
    if settings.use_mock_fhir:
        from mocks import fhir_mock
        return await fhir_mock.lookup(request)

    # Real FHIR R4 implementation (Phase 5 / production hardening)
    raise NotImplementedError("Real FHIR client not yet implemented — set USE_MOCK_FHIR=true")


async def create_patient(request: PatientCreateRequest) -> PatientCreateResponse:
    """Route patient creation to mock or real FHIR R4 server."""
    if settings.use_mock_fhir:
        from mocks import fhir_mock
        return await fhir_mock.create(request)

    raise NotImplementedError("Real FHIR client not yet implemented — set USE_MOCK_FHIR=true")
