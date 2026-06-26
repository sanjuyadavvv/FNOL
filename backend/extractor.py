import re
from typing import Any

import pdfplumber

from date_utils import build_date_validation, find_invalid_dates

MANDATORY_FIELDS = [
    "policyNumber",
    "policyholderName",
    "effectiveDates",
    "incidentDate",
    "incidentTime",
    "location",
    "description",
    "claimant",
    "contactDetails",
    "assetType",
    "assetId",
    "estimatedDamage",
    "claimType",
    "attachments",
    "initialEstimate",
]

DATE_ISO = r"\d{4}-\d{2}-\d{2}"
DATE_NUMERIC = r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"
DATE_TEXT = (
    r"[A-Za-z]+\s*\d{1,2},?\s*\d{4}|"
    r"[A-Za-z]+\d{1,2}\s+\d{4}|"
    r"\d{1,2}\s+[A-Za-z]+\s+\d{4}"
)
DATE_ANY = rf"(?:{DATE_ISO}|{DATE_NUMERIC}|{DATE_TEXT})"

# FIX 1: Added "Vehicle\s*Information" to SECTION_END so description
# terminates correctly when followed by "Vehicle Information:" block
SECTION_END = (
    r"Claimant|Third|Asset|Vehicle\s*Information|Vehicle|Other\s*Party|Police|"
    r"Injuries|Witnesses|Reported|Claim\s*Type|Attachments|Initial|"
    r"Make|Model|Year|VIN|License\s*Plate|Insurance\s*Company|Policy\s*Number|"
    r"Contact|Estimated|Damage\s*Estimate"
)

DESCRIPTION_START = re.compile(
    r"(?:Description\s+of\s+(?:Loss|Incident)|Incident\s+Description|Description)\s*[:\-]?\s*",
    re.IGNORECASE,
)
DESCRIPTION_NEXT_SECTION = re.compile(
    rf"^\s*(?:{SECTION_END})\b",
    re.IGNORECASE | re.MULTILINE,
)

FIELD_PATTERNS: dict[str, list[str]] = {
    "policyNumber": [
        r"Policy\s*(?:Number|No\.?|#)\s*[:\-]?\s*([A-Z0-9\-]+)",
        r"POL[-\s]?(\d{4,})",
    ],
    "policyholderName": [
        r"Policyholder\s*Name\s*[:\-]?\s*([^\n]+)",
        r"Insured\s*Name\s*[:\-]?\s*([^\n]+)",
        r"Name\s*of\s*Insured\s*[:\-]?\s*([^\n]+)",
    ],
    "effectiveDates": [
        r"Effective\s*Dates?\s*[:\-]?\s*([^\n]+)",
        r"Policy\s*Period\s*[:\-]?\s*([^\n]+)",
    ],
    "incidentDate": [
        rf"Incident\s*Date\s*[:\-]?\s*({DATE_ANY})",
        rf"Date\s*of\s*(?:Loss|Incident)\s*[:\-]?\s*({DATE_ANY})",
    ],
    "incidentTime": [
        r"Incident\s*Time\s*[:\-]?\s*(\d{1,2}:\d{2}(?:\s*[AP]M)?)",
        r"Time\s*of\s*(?:Loss|Incident)\s*[:\-]?\s*(\d{1,2}:\d{2}(?:\s*[AP]M)?)",
    ],
    "location": [
        r"Location\s*of\s*Loss\s*[:\-]?\s*([^\n]+)",
        r"Location\s*[:\-]?\s*([^\n]+)",
        r"Place\s*of\s*(?:Loss|Incident)\s*[:\-]?\s*([^\n]+)",
    ],
    # Description is extracted by _extract_description() — not via generic patterns
    "claimant": [
        r"Claimant\s*Name\s*[:\-]?\s*([^\n]+)",
        r"Claimant\s*[:\-]?\s*([^\n]+)",
        r"Name\s*of\s*Claimant\s*[:\-]?\s*([^\n]+)",
    ],
    "thirdParties": [
        r"Other\s*Party\s*Information\s*:?\s*\nName\s*[:\-]?\s*([^\n]+)",
        r"Third\s*Part(?:y|ies)\s*[:\-]?\s*([^\n]+)",
        r"Other\s*Parties?\s*[:\-]?\s*([^\n]+)",
    ],
    "contactDetails": [
        r"Contact\s*Details?\s*[:\-]?\s*([^\n]+)",
    ],
    "claimantPhone": [
        r"Claimant\s*Phone\s*[:\-]?\s*([^\n]+)",
        r"(?:Phone|Tel)\s*[:\-]?\s*([^\n]+)",
    ],
    "claimantEmail": [
        r"Claimant\s*Email\s*[:\-]?\s*([^\n]+)",
        r"Email\s*[:\-]?\s*([\w.\-+]+@[\w.\-]+\.\w+)",
    ],
    "assetType": [
        r"Asset\s*Type\s*[:\-]?\s*([^\n]+)",
        r"Type\s*of\s*Asset\s*[:\-]?\s*([^\n]+)",
    ],
    "assetId": [
        r"Asset\s*(?:ID|Identifier)\s*[:\-]?\s*([A-Z0-9\-]+)",
        r"VIN\s*[:\-]?\s*([A-Z0-9]{11,17})",
    ],
    "estimatedDamage": [
        r"Estimated\s*Damage\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
        r"Damage\s*Estimate\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
    ],
    "claimType": [
        r"Claim\s*Type\s*[:\-]?\s*([^\n]+)",
        r"Type\s*of\s*Claim\s*[:\-]?\s*([^\n]+)",
    ],
    "attachments": [
        r"Attachments?\s*[:\-]?\s*([^\n]+)",
        r"Documents?\s*Attached\s*[:\-]?\s*([^\n]+)",
    ],
    "initialEstimate": [
        r"Initial\s*Estimate\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
        r"Preliminary\s*Estimate\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
    ],
    # FIX 3: Use [^\n]+ instead of .+?(?:\n) for all single-line vehicle fields
    "vehicleMake": [r"Make\s*[:\-]?\s*([^\n]+)"],
    "vehicleModel": [r"Model\s*[:\-]?\s*([^\n]+)"],
    "vehicleYear": [r"Year\s*[:\-]?\s*(\d{4})"],
    # FIX 4: Use [^\n]+ for police report fields so they extract reliably
    "policeReportFiled": [r"Police\s*Report\s*Filed\s*[:\-]?\s*([^\n]+)"],
    "policeReportNumber": [r"Police\s*Report\s*Number\s*[:\-]?\s*([^\n]+)"],
    "otherPartyInsurance": [
        r"Other\s*Party\s*Information\s*:?\s*\nName\s*[:\-]?\s*.+?\n"
        r"Insurance\s*Company\s*[:\-]?\s*([^\n]+)",
    ],
}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    import io

    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    if lower.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="replace")
    raise ValueError("Unsupported file type. Please upload a PDF or TXT file.")


def _match_field(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            value = re.sub(r"\s+", " ", value)
            if value and value.lower() not in ("n/a", "none", "—", "-"):
                return value
    return None


def _extract_description(text: str) -> str | None:
    """
    Extract multi-line description for both 'Description:' and 'Description of Loss:'.
    Stops at the next recognised section header or end of document.
    """
    match = DESCRIPTION_START.search(text)
    if not match:
        return None

    rest = text[match.end():]
    next_section = DESCRIPTION_NEXT_SECTION.search(rest)
    chunk = rest[: next_section.start()] if next_section else rest
    chunk = chunk.strip()
    chunk = re.sub(r"\s+", " ", chunk)

    if chunk and chunk.lower() not in ("n/a", "none", "—", "-"):
        return chunk
    return None


def parse_damage_amount(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _enrich_flat_fields(text: str, flat: dict[str, str | None]) -> dict[str, str | None]:
    """Fill gaps using alternate labels and composite fields."""
    description = _extract_description(text)
    if description:
        flat["description"] = description

    phone = flat.get("claimantPhone") or _match_field(text, FIELD_PATTERNS["claimantPhone"])
    email = flat.get("claimantEmail") or _match_field(text, FIELD_PATTERNS["claimantEmail"])
    if not flat.get("contactDetails") and (phone or email):
        flat["contactDetails"] = ", ".join(part for part in (phone, email) if part)

    # FIX 3 (continued): vehicleMake/Model/Year now use [^\n]+ patterns above,
    # so this enrichment reliably builds assetType from vehicle fields
    if not flat.get("assetType"):
        make = flat.get("vehicleMake") or _match_field(text, FIELD_PATTERNS["vehicleMake"])
        model = flat.get("vehicleModel") or _match_field(text, FIELD_PATTERNS["vehicleModel"])
        year = flat.get("vehicleYear") or _match_field(text, FIELD_PATTERNS["vehicleYear"])
        if make and model:
            flat["assetType"] = f"{make} {model}" + (f" {year}" if year else "")

    if not flat.get("thirdParties"):
        name = _match_field(text, FIELD_PATTERNS["thirdParties"])
        insurance = _match_field(text, FIELD_PATTERNS["otherPartyInsurance"])
        if name:
            flat["thirdParties"] = name + (f" ({insurance})" if insurance else "")

    # FIX 4 (continued): police report fields now extract reliably with [^\n]+
    # so attachments enrichment will fire correctly
    if not flat.get("attachments"):
        filed = _match_field(text, FIELD_PATTERNS["policeReportFiled"])
        report_no = _match_field(text, FIELD_PATTERNS["policeReportNumber"])
        parts: list[str] = []
        if filed and filed.lower() not in ("no", "false"):
            parts.append("Police report filed")
        if report_no:
            parts.append(f"Police Report #{report_no}")
        if parts:
            flat["attachments"] = ", ".join(parts)

    # claimType fallback: fires once assetId (VIN) or assetType is resolved
    if not flat.get("claimType") and (flat.get("assetId") or flat.get("assetType")):
        flat["claimType"] = "Auto Collision"

    return flat


def extract_fields(text: str) -> dict[str, Any]:
    flat: dict[str, str | None] = {}
    for field, patterns in FIELD_PATTERNS.items():
        flat[field] = _match_field(text, patterns)

    flat = _enrich_flat_fields(text, flat)

    damage = parse_damage_amount(flat.get("estimatedDamage"))
    initial = parse_damage_amount(flat.get("initialEstimate"))

    return {
        "policyInformation": {
            "policyNumber": flat.get("policyNumber"),
            "policyholderName": flat.get("policyholderName"),
            "effectiveDates": flat.get("effectiveDates"),
        },
        "incidentInformation": {
            "date": flat.get("incidentDate"),
            "time": flat.get("incidentTime"),
            "location": flat.get("location"),
            "description": flat.get("description"),
        },
        "involvedParties": {
            "claimant": flat.get("claimant"),
            "thirdParties": flat.get("thirdParties"),
            "contactDetails": flat.get("contactDetails"),
        },
        "assetDetails": {
            "assetType": flat.get("assetType"),
            "assetId": flat.get("assetId"),
            "estimatedDamage": flat.get("estimatedDamage"),
            "estimatedDamageNumeric": damage,
        },
        "other": {
            "claimType": flat.get("claimType"),
            "attachments": flat.get("attachments"),
            "initialEstimate": flat.get("initialEstimate"),
            "initialEstimateNumeric": initial,
        },
    }


def find_missing_fields(extracted: dict[str, Any]) -> list[str]:
    flat_map = {
        "policyNumber": extracted["policyInformation"]["policyNumber"],
        "policyholderName": extracted["policyInformation"]["policyholderName"],
        "effectiveDates": extracted["policyInformation"]["effectiveDates"],
        "incidentDate": extracted["incidentInformation"]["date"],
        "incidentTime": extracted["incidentInformation"]["time"],
        "location": extracted["incidentInformation"]["location"],
        "description": extracted["incidentInformation"]["description"],
        "claimant": extracted["involvedParties"]["claimant"],
        "contactDetails": extracted["involvedParties"]["contactDetails"],
        "assetType": extracted["assetDetails"]["assetType"],
        "assetId": extracted["assetDetails"]["assetId"],
        "estimatedDamage": extracted["assetDetails"]["estimatedDamage"],
        "claimType": extracted["other"]["claimType"],
        "attachments": extracted["other"]["attachments"],
        "initialEstimate": extracted["other"]["initialEstimate"],
    }
    return [field for field in MANDATORY_FIELDS if not flat_map.get(field)]


def process_document_text(text: str) -> dict[str, Any]:
    extracted = extract_fields(text)
    missing = find_missing_fields(extracted)
    date_validation = build_date_validation(extracted)
    invalid_dates = find_invalid_dates(date_validation)

    return {
        "extractedFields": extracted,
        "missingFields": missing,
        "dateValidation": date_validation,
        "invalidDates": invalid_dates,
    }