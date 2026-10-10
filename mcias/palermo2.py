"""Palermo-2: independent, fail-closed G5 financial and evidence reconciliation."""
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from mcias.audit_agents import AGENTS

def _finite(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return number if number.is_finite() and number >= 0 else None

def verify(claim, findings, calculation):
    issues = []
    if (not isinstance(findings, list) or len(findings) != len(AGENTS)
        or {x.get("agent") for x in findings if isinstance(x, dict)} != set(AGENTS)):
        issues.append("missing_or_duplicate_agent")
    if (not isinstance(findings, list)
        or any(not isinstance(x, dict) or x.get("status") != "pass" for x in findings)):
        issues.append("unresolved_findings")
    if not isinstance(calculation, dict) or calculation.get("status") != "calculated":
        issues.append("calculation_held")
        calculation = calculation if isinstance(calculation, dict) else {}
    else:
        original = _finite(claim.claimed_amount)
        claimed = _finite(calculation.get("claimed"))
        payable = _finite(calculation.get("payable"))
        steps = calculation.get("deductions")
        deductions = ([_finite(x.get("deduction")) if isinstance(x, dict) else None
                       for x in steps] if isinstance(steps, list) else [None])
        if (original is None or claimed is None or payable is None
            or any(x is None for x in deductions) or claimed != original):
            issues.append("invalid_monetary_values")
        else:
            if sum(deductions, Decimal(0)) + payable != claimed:
                issues.append("T09_financial_reconciliation_failed")
            disclosed_total = _finite(calculation.get("total_deduction"))
            if disclosed_total is None or disclosed_total != sum(deductions, Decimal(0)):
                issues.append("deduction_total_mismatch")
        if calculation.get("source_id") != claim.extracted_record_id:
            issues.append("source_mismatch")
        if calculation.get("currency") != claim.currency:
            issues.append("currency_mismatch")
        fingerprint = calculation.get("fingerprint")
        payload = {k: v for k, v in calculation.items() if k != "fingerprint"}
        try:
            expected = sha256(json.dumps(payload, sort_keys=True,
                separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        except (ValueError, TypeError):
            expected = None
        if fingerprint != expected or expected is None:
            issues.append("calculation_fingerprint_mismatch")
    return {"status": "verified" if not issues else "held",
            "issues": issues, "claim_id": claim.id,
            "calculation_fingerprint": calculation.get("fingerprint")}
