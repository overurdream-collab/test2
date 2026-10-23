"""G4 strict source-record normalization. No guessed clinical or monetary values."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re

FIELDS=("claim_reference","beneficiary_token","provider_code","service_code",
        "service_date","claimed_amount","currency")

class ClaimValidationError(ValueError):
    pass

def source_decimal(value, *, allow_percent=False):
    """Accept explicit decimal amounts and unambiguous three-digit grouping."""
    raw=str(value).strip()
    if allow_percent:raw=raw.removesuffix('%').strip()
    if ',' in raw and not re.fullmatch(r'[0-9]{1,3}(,[0-9]{3})+(\.[0-9]{1,4})?',raw):
        raise ClaimValidationError('ambiguous numeric grouping')
    try:number=Decimal(raw.replace(',',''))
    except InvalidOperation:raise ClaimValidationError('invalid source number') from None
    if not number.is_finite() or number<0 or number>=Decimal('100000000000000') or number.as_tuple().exponent < -4:
        raise ClaimValidationError('source number out of range or precision')
    return number

def normalize(values: dict, mapping=None) -> dict:
    if not isinstance(values,dict):
        raise ClaimValidationError("record is not a mapping")
    if mapping:
        # The original source dict is never changed. Column choices and currency
        # are confirmed by the operator, not guessed from the invoice text.
        try:
            data={field:str(values[source]).strip() for field,source in mapping['columns'].items()}
            data['currency']=mapping['currency']
            raw=data['service_date']
            if mapping['date_format']=='DMY':
                data['service_date']=datetime.strptime(raw,'%d/%m/%Y').date().isoformat()
            elif mapping['date_format']=='YMD_SLASH':
                data['service_date']=datetime.strptime(raw,'%Y/%m/%d').date().isoformat()
            else:
                data['service_date']=datetime.fromisoformat(raw).date().isoformat()
            data['claimed_amount']=format(source_decimal(data['claimed_amount']),'f')
            values=data
        except (KeyError,TypeError,ValueError):
            raise ClaimValidationError('source values do not match the confirmed mapping') from None
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
