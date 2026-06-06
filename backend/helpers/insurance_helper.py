from __future__ import annotations

from config import settings
from models.insurance import InsuranceCheckRequest, InsuranceCheckResponse


async def check_insurance(request: InsuranceCheckRequest) -> InsuranceCheckResponse:
    """Route insurance eligibility check to mock or real eligibility API."""
    if settings.use_mock_insurance:
        from mocks import insurance_mock
        return await insurance_mock.check(request)

    raise NotImplementedError("Real insurance client not yet implemented — set USE_MOCK_INSURANCE=true")
