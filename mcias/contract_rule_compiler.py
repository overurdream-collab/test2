"""Allowlisted Contract Intelligence typed diagnostic. No financial activation."""
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re

class CompilationBlocked(ValueError):
    pass

def _decimal(value):
    if type(value) not in (str, int, Decimal):
        raise CompilationBlocked("numeric type must be explicit")
    try:
        number=Decimal(str(value))
    except (InvalidOperation,ValueError):
        raise CompilationBlocked("invalid numeric value") from None
    if not number.is_finite() or number < 0 or number >= Decimal("100000000000000") or number.as_tuple().exponent < -4:
        raise CompilationBlocked("numeric range or precision invalid")
    return number

def _fingerprint(ast):
    data={key:value for key,value in ast.items() if key!="fingerprint"}
    return sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def compile_diagnostic(point, *, end_override=None):
    """Only separately approved SOURCE-LINKED tariff/copay terms; not executable."""
    org=getattr(point,"organization_id",None)
    start=getattr(point,"effective_from",None)
    end=end_override or getattr(point,"effective_until",None)
    source=getattr(point,"source_sha256",None)
    if (getattr(point,"status",None)!="approved" or not isinstance(org,str) or not org
        or not isinstance(source,str) or re.fullmatch("[0-9a-f]{64}",source) is None
        or not isinstance(start,date) or not isinstance(end,date) or start>=end):
        raise CompilationBlocked("approved, dated, source-linked tenant clause required")
    section=getattr(point,"section",None)
    key=getattr(point,"logical_key",None)
    provider=getattr(point,"provider_code",None)
    service=getattr(point,"service_code",None)
    currency=getattr(point,"currency",None)
    amount=_decimal(getattr(point,"amount",None))
    if section=="tariffs":
        if (getattr(point,"rule_type",None)!="amount" or
            not isinstance(provider,str) or not provider or not isinstance(service,str) or not service
            or key!=provider+":"+service or
            not isinstance(currency,str) or re.fullmatch("[A-Z]{3}",currency) is None):
            raise CompilationBlocked("unverifiable provider tariff scope")
        op="MATCH_G3_AND_G5_TARIFF"
    elif section=="cost_sharing":
        keys={"copay_percent"}
        if isinstance(provider,str):
            keys.add(provider+":copay_percent")
            if isinstance(service,str):
                keys.add(provider+":"+service+":copay_percent")
        if (getattr(point,"rule_type",None)!="percentage" or amount>100
            or key not in keys or currency is not None):
            raise CompilationBlocked("unverifiable copay basis")
        op="MATCH_G5_COPAY"
    else:
        raise CompilationBlocked("ambiguous or unsupported clause requires human review")
    ast={"organization_id":org,"reference_point_id":str(point.id),"version":int(point.version),
         "source_sha256":source,"operation":op,"provider_code":provider,
         "service_code":service,"currency":currency,"expected":format(amount,"f"),
         "effective_from":start.isoformat(),"effective_until":end.isoformat(),
         "status":"DIAGNOSTIC_ONLY","execution_authorized":False}
    ast["fingerprint"]=_fingerprint(ast)
    return ast

def compare_diagnostic(ast, *, organization_id, provider_code, service_code, service_date,
                       currency, g3_tariff=None, g5_tariff=None, g5_copay=None):
    """Pure consistency check against caller-provided data; no signature verification."""
    if (not isinstance(ast,dict) or ast.get("status")!="DIAGNOSTIC_ONLY"
        or ast.get("execution_authorized") is not False
        or ast.get("fingerprint")!=_fingerprint(ast)):
        return {"status":"INDETERMINATE","reason":"invalid_diagnostic_ast"}
    if organization_id!=ast["organization_id"]:
        return {"status":"INDETERMINATE","reason":"tenant_mismatch"}
    if not isinstance(service_date,date):
        return {"status":"INDETERMINATE","reason":"unknown_service_date"}
    if not (ast["effective_from"]<=service_date.isoformat()<ast["effective_until"]):
        return {"status":"NOT_APPLICABLE","reason":"historical_period"}
    if ast["provider_code"] is not None and provider_code!=ast["provider_code"]:
        return {"status":"NOT_APPLICABLE","reason":"provider_mismatch"}
    if ast["service_code"] is not None and service_code!=ast["service_code"]:
        return {"status":"NOT_APPLICABLE","reason":"service_mismatch"}
    if ast["operation"]=="MATCH_G3_AND_G5_TARIFF":
        if currency!=ast["currency"] or g3_tariff is None or g5_tariff is None:
            return {"status":"INDETERMINATE","reason":"unverified_financial_authority"}
        actual=(_decimal(g3_tariff),_decimal(g5_tariff))
    elif ast["operation"]=="MATCH_G5_COPAY":
        if g5_copay is None:
            return {"status":"INDETERMINATE","reason":"no_approved_copay_input"}
        actual=(_decimal(g5_copay),)
    else:
        return {"status":"INDETERMINATE","reason":"not_allowlisted"}
    return {"status":"CONSISTENT" if all(v==Decimal(ast["expected"]) for v in actual) else "CONFLICT",
            "reason":"advisory_only","execution_authorized":False,"fingerprint":ast["fingerprint"]}
