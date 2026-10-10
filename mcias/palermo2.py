"""Palermo-2 independent reconciliation and evidence gate."""
from decimal import Decimal
from hashlib import sha256
import json

def verify(claim,findings,calculation):
    issues=[]
    if len(findings)!=8 or len({x["agent"] for x in findings})!=8:
        issues.append("missing_or_duplicate_agent")
    if any(x["status"]!="pass" for x in findings):
        issues.append("unresolved_findings")
    if calculation["status"]!="calculated":
        issues.append("calculation_held")
    else:
        original=Decimal(str(claim.claimed_amount))
        claimed=Decimal(calculation["claimed"])
        payable=Decimal(calculation["payable"])
        deductions=[Decimal(x["deduction"]) for x in calculation["deductions"]]
        if claimed!=original or payable<0 or any(x<0 for x in deductions):
            issues.append("invalid_monetary_values")
        if sum(deductions,Decimal(0))+payable!=claimed:
            issues.append("T09_financial_reconciliation_failed")
        if calculation["source_id"]!=claim.extracted_record_id:
            issues.append("source_mismatch")
        if calculation["currency"]!=claim.currency:
            issues.append("currency_mismatch")
        fingerprint=calculation.get("fingerprint")
        payload={k:v for k,v in calculation.items() if k!="fingerprint"}
        expected=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if fingerprint!=expected:
            issues.append("calculation_fingerprint_mismatch")
    return {"status":"verified" if not issues else "held","issues":issues,
            "claim_id":claim.id,"calculation_fingerprint":calculation.get("fingerprint")}
