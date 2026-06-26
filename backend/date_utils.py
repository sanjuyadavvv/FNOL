import re
from datetime import datetime

MONTH_MAP: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

NUMERIC_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%m/%d/%y",
    "%m-%d-%y",
    "%d/%m/%Y",
    "%d-%m-%Y",
)


def _from_month_name(month_str: str, day: int, year: int) -> datetime | None:
    month = MONTH_MAP.get(month_str.lower())
    if not month:
        return None
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def parse_flexible_date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None

    for fmt in NUMERIC_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    # May 1, 2026 | May 1 2026 | may 1 2026
    match = re.match(r"^([A-Za-z]+)\s*(\d{1,2}),?\s*(\d{4})$", value, re.IGNORECASE)
    if match:
        return _from_month_name(match.group(1), int(match.group(2)), int(match.group(3)))

    # may1 2026 | May1 2026
    match = re.match(r"^([A-Za-z]+)(\d{1,2})\s+(\d{4})$", value, re.IGNORECASE)
    if match:
        return _from_month_name(match.group(1), int(match.group(2)), int(match.group(3)))

    # 1 May 2026
    match = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", value, re.IGNORECASE)
    if match:
        return _from_month_name(match.group(2), int(match.group(1)), int(match.group(3)))

    return None


def validate_date(value: str | None) -> dict:
    if not value or not value.strip():
        return {
            "raw": value,
            "normalized": None,
            "valid": False,
            "error": "Date not provided",
        }

    raw = value.strip()
    parsed = parse_flexible_date(raw)
    if parsed:
        return {
            "raw": raw,
            "normalized": parsed.strftime("%Y-%m-%d"),
            "valid": True,
            "error": None,
        }

    return {
        "raw": raw,
        "normalized": None,
        "valid": False,
        "error": f'Unrecognized date format: "{raw}"',
    }


def validate_date_range(value: str | None) -> dict:
    if not value or not value.strip():
        return {
            "raw": value,
            "valid": False,
            "error": "Date range not provided",
            "start": None,
            "end": None,
        }

    raw = value.strip()
    parts = re.split(r"\s*(?:-|–|—|to|through)\s*", raw, maxsplit=1)

    if len(parts) == 1:
        single = validate_date(parts[0].strip())
        return {
            "raw": raw,
            "valid": single["valid"],
            "error": single["error"],
            "start": single,
            "end": None,
        }

    start = validate_date(parts[0].strip())
    end = validate_date(parts[1].strip())
    valid = start["valid"] and end["valid"]
    error = None
    if not start["valid"]:
        error = f"Invalid start date: {start['error']}"
    elif not end["valid"]:
        error = f"Invalid end date: {end['error']}"

    return {
        "raw": raw,
        "valid": valid,
        "error": error,
        "start": start,
        "end": end,
    }


def build_date_validation(extracted: dict) -> dict:
    return {
        "incidentDate": validate_date(extracted["incidentInformation"]["date"]),
        "effectiveDates": validate_date_range(
            extracted["policyInformation"]["effectiveDates"]
        ),
    }


def find_invalid_dates(date_validation: dict) -> list[str]:
    invalid: list[str] = []
    incident = date_validation["incidentDate"]
    if incident["raw"] and not incident["valid"]:
        invalid.append("incidentDate")

    effective = date_validation["effectiveDates"]
    if effective["raw"] and not effective["valid"]:
        invalid.append("effectiveDates")

    return invalid
