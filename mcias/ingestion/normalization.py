"""Versioned source normalization without mutating original values."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

def decimal_value(raw: str) -> str | None:
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip().replace(",", "")
    try:
        value = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite():
        return None
    return format(value, "f")

def iso_date(raw: str) -> str | None:
    if not isinstance(raw, str):
        return None
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw.strip(), pattern).date().isoformat()
        except ValueError:
            continue
    return None

def normalize_fields(values: dict[str, str], numeric_fields=(), date_fields=()) -> dict:
    result = {"original": dict(values), "normalized": {}, "errors": {}}
    for key in numeric_fields:
        value = decimal_value(values.get(key))
        if value is None:
            result["errors"][key] = "invalid decimal"
        else:
            result["normalized"][key] = value
    for key in date_fields:
        value = iso_date(values.get(key))
        if value is None:
            result["errors"][key] = "invalid date"
        else:
            result["normalized"][key] = value
    return result
