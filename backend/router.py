import re
from dataclasses import dataclass
from typing import Any

INVESTIGATION_KEYWORDS_RE = re.compile(r'\b(?:fraud|inconsistent|staged)\b')
FAST_TRACK_THRESHOLD = 25_000
CURRENCY_SYMBOL = "$"


@dataclass(frozen=True)
class RouteDecision:
    queue: str
    reason: str


def normalize_keys(d: dict) -> dict:
    return {
        k.lower(): normalize_keys(v) if isinstance(v, dict) else v
        for k, v in d.items()
    }


def determine_route(extracted: dict[str, Any], missing_fields: list[str]) -> RouteDecision:
    extracted = normalize_keys(extracted)

    description = (extracted.get("incidentinformation", {}).get("description") or "").lower()
    claim_type  = (extracted.get("other", {}).get("claimtype") or "").lower()
    damage      = extracted.get("assetdetails", {}).get("estimateddamagenumeric")
    initial     = extracted.get("other", {}).get("initialestimatednumeric")
    estimate    = damage if damage is not None else initial

    if missing_fields:
        missing_list = ", ".join(missing_fields)
        return RouteDecision(
            queue="Manual Review",
            reason=f"Mandatory fields missing ({missing_list}); requires manual review.",
        )

    match = INVESTIGATION_KEYWORDS_RE.search(description)
    if match:
        return RouteDecision(
            queue="Investigation Flag",
            reason=f'Description contains "{match.group()}", triggering investigation review.',
        )

    if "injury" in claim_type:
        return RouteDecision(
            queue="Specialist Queue",
            reason="Claim type is injury-related; routed to specialist handling.",
        )

    if estimate is not None and 0 < estimate < FAST_TRACK_THRESHOLD:
        return RouteDecision(
            queue="Fast-track",
            reason=(
                f"Estimated damage ({CURRENCY_SYMBOL}{estimate:,.2f}) is below "
                f"{CURRENCY_SYMBOL}{FAST_TRACK_THRESHOLD:,}; eligible for fast-track processing."
            ),
        )

    if estimate is not None:
        return RouteDecision(
            queue="Standard Review",
            reason=(
                f"Estimated damage ({CURRENCY_SYMBOL}{estimate:,.2f}) is at or above "
                f"{CURRENCY_SYMBOL}{FAST_TRACK_THRESHOLD:,}; routed to standard review."
            ),
        )

    return RouteDecision(
        queue="Standard Review",
        reason="All mandatory fields present; routed to standard review.",
    )


def format_output(
    extracted: dict[str, Any],
    missing_fields: list[str],
    decision: RouteDecision,
) -> dict:
    return {
        "extractedFields": extracted,
        "missingFields": missing_fields,
        "recommendedRoute": decision.queue,
        "reasoning": decision.reason,
    }