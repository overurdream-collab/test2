"""G4 strict source-record normalization. No guessed clinical or monetary values."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re

FIELDS=("claim_reference","beneficiary_token","provider_code","service_code",
        "service_date","claimed_amount","currency")

class ClaimValidationError(ValueError):
    pass

def normalize(values: dict) -> dict:
    if not isinstance(values,dict):
        raise ClaimValidationError("record is not a mapping")
    missing=[key for key in FIELDS if key not in values or not isinstance(values[key],str) or not values[key].strip()]
    if missing:
        raise ClaimValidationError("missing required fields: "+",".join(missing))
    data={key:values[key].strip() for key in FIELDS}
    for key,limit in (("claim_reference",120),("beneficiary_token",128),("provider_code",80),("service_code",100)):
        if len(data[key])>limit or any(ord(c)<32 for c in data[key]):
            raise ClaimValidationError("invalid "+key)
    if not re.fullmatch(r"[A-Z]{3}",data["currency"]):
        raise ClaimValidationError("invalid currency")
    try:
        day=date.fromisoformat(data["service_date"])
    except ValueError as exc:
        raise ClaimValidationError("service_date must be ISO YYYY-MM-DD") from exc
    if day.isoformat()!=data["service_date"]:
        raise ClaimValidationError("noncanonical service date")
    try:
        amount=Decimal(data["claimed_amount"])
    except InvalidOperation as exc:
        raise ClaimValidationError("invalid claimed amount") from exc
    if not amount.is_finite() or amount<0 or amount>=Decimal("100000000000000") or amount.as_tuple().exponent < -4:
        raise ClaimValidationError("claimed amount out of range or precision")
    data["service_date"]=day
    data["claimed_amount"]=amount
    return data
