"""Deterministic tariff batch validation; no implicit partial financial changes."""
import csv
import io
from decimal import Decimal, InvalidOperation

class TariffImportError(ValueError):
    pass

def preview_csv(data: bytes) -> dict:
    if len(data) > 2_000_000:
        raise TariffImportError("tariff CSV exceeds 2 MB")
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TariffImportError("UTF-8 required") from exc
    reader = csv.DictReader(io.StringIO(content, newline=""), strict=True)
    if reader.fieldnames != ["service_code", "amount", "currency"]:
        raise TariffImportError("expected service_code,amount,currency headers")
    accepted, errors, seen = [], [], set()
    try:
        for index, row in enumerate(reader, start=2):
            if index > 10001:
                raise TariffImportError("row limit exceeded")
            if None in row or any(value is None for value in row.values()):
                errors.append({"row": index, "reason": "invalid column count"})
                continue
            code, raw, currency = (row[key].strip() for key in reader.fieldnames)
            if not code or len(code) > 100 or code in seen:
                errors.append({"row": index, "reason": "empty, duplicate or oversized service code"})
                continue
            seen.add(code)
            try:
                amount = Decimal(raw)
                valid = amount.is_finite() and 0 <= amount < Decimal("100000000000000") and amount.as_tuple().exponent >= -4
            except InvalidOperation:
                valid = False
            if not valid or len(currency) != 3 or not currency.isalpha() or currency != currency.upper():
                errors.append({"row": index, "reason": "invalid amount precision or currency"})
                continue
            accepted.append({"row": index, "service_code": code, "amount": format(amount, "f"), "currency": currency})
    except csv.Error as exc:
        raise TariffImportError("malformed CSV") from exc
    return {"accepted": accepted, "errors": errors, "complete": not errors, "rows_seen": len(accepted) + len(errors)}
