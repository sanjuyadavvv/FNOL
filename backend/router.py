from typing import Any

INVESTIGATION_KEYWORDS = ("fraud", "inconsistent", "staged")
FAST_TRACK_THRESHOLD = 25_000


def determine_route(extracted: dict[str, Any], missing_fields: list[str]) -> tuple[str, str]:
    description = (extracted.get("incidentInformation", {}).get("description") or "").lower()
    claim_type = (extracted.get("other", {}).get("claimType") or "").lower()
    damage = extracted.get("assetDetails", {}).get("estimatedDamageNumeric")
    initial = extracted.get("other", {}).get("initialEstimateNumeric")
    estimate = damage if damage is not None else initial

    reasons: list[str] = []

    for keyword in INVESTIGATION_KEYWORDS:
        if keyword in description:
            reasons.append(
                f'Description contains "{keyword}", triggering investigation review.'
            )
            return "Investigation Flag", " ".join(reasons)

    if "injury" in claim_type:
        reasons.append("Claim type is injury-related; routed to specialist handling.")
        return "Specialist Queue", " ".join(reasons)

    if missing_fields:
        missing_list = ", ".join(missing_fields)
        reasons.append(
            f"Mandatory fields missing ({missing_list}); requires manual review."
        )
        return "Manual Review", " ".join(reasons)

    if estimate is not None and estimate < FAST_TRACK_THRESHOLD:
        reasons.append(
            f"Estimated damage (${estimate:,.2f}) is below ${FAST_TRACK_THRESHOLD:,}; "
            "eligible for fast-track processing."
        )
        return "Fast-track", " ".join(reasons)

    if estimate is not None:
        reasons.append(
            f"Estimated damage (${estimate:,.2f}) meets or exceeds ${FAST_TRACK_THRESHOLD:,}; "
            "standard processing queue."
        )
        return "Standard Processing", " ".join(reasons)

    reasons.append("All mandatory fields present; routed to standard processing.")
    return "Standard Processing", " ".join(reasons)
