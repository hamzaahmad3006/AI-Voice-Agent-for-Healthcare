from __future__ import annotations

from datetime import datetime, timezone

from models.insurance import (
    EligibilityStatus,
    InsuranceCheckRequest,
    InsuranceCheckResponse,
)

# ---------------------------------------------------------------------------
# Rules-based eligibility mock — no external call needed
# ---------------------------------------------------------------------------

# Known payers → ELIGIBLE in-network
_ELIGIBLE_PAYERS: frozenset[str] = frozenset({
    "bluecross", "blue cross", "bcbs", "aetna", "cigna", "united", "unitedhealthcare",
    "humana", "kaiser", "anthem", "centene", "cvs health", "molina",
})

# Known payers → INELIGIBLE (expired / not contracted)
_INELIGIBLE_PAYERS: frozenset[str] = frozenset({
    "expired_plan", "test_ineligible", "no_coverage",
})

# self_pay → ELIGIBLE (no insurance, patient pays directly)
_SELF_PAY_KEY = "self_pay"

# Member IDs that trigger UNKNOWN (e.g. eligibility system unavailable)
_UNKNOWN_MEMBER_PREFIXES: tuple[str, ...] = ("UNK-", "BAD-", "ERR-")


async def check(request: InsuranceCheckRequest) -> InsuranceCheckResponse:
    """Evaluate eligibility using simple deterministic rules."""
    now = datetime.now(timezone.utc).isoformat()
    payer_key = request.payer_name.lower().strip()

    if payer_key == _SELF_PAY_KEY:
        return InsuranceCheckResponse(
            eligibility=EligibilityStatus.ELIGIBLE,
            in_network=True,
            plan_name="Self Pay",
            checked_at=now,
            notes="Patient is self-pay — no insurance verification needed.",
            requires_staff_verification=False,
        )

    # Member ID prefix check for forced UNKNOWN
    if any(request.member_id.startswith(p) for p in _UNKNOWN_MEMBER_PREFIXES):
        return InsuranceCheckResponse(
            eligibility=EligibilityStatus.UNKNOWN,
            in_network=None,
            plan_name=None,
            checked_at=now,
            notes="Eligibility could not be verified — flagged for staff review.",
            requires_staff_verification=True,
        )

    if payer_key in _INELIGIBLE_PAYERS:
        return InsuranceCheckResponse(
            eligibility=EligibilityStatus.INELIGIBLE,
            in_network=False,
            plan_name=None,
            checked_at=now,
            notes="Plan not active or not contracted with this provider.",
            requires_staff_verification=False,
        )

    if payer_key in _ELIGIBLE_PAYERS:
        return InsuranceCheckResponse(
            eligibility=EligibilityStatus.ELIGIBLE,
            in_network=True,
            plan_name=request.payer_name.title(),
            checked_at=now,
            notes=None,
            requires_staff_verification=False,
        )

    # Unknown payer — treat as UNKNOWN, flag for staff
    return InsuranceCheckResponse(
        eligibility=EligibilityStatus.UNKNOWN,
        in_network=None,
        plan_name=None,
        checked_at=now,
        notes=f"Payer '{request.payer_name}' not found in contracted network list.",
        requires_staff_verification=True,
    )
