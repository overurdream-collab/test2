"""G5 golden financial fixtures: deterministic ordering and independent verification."""
from decimal import Decimal
from types import SimpleNamespace
import pytest
from mcias.audit_engine import AuditPolicy, PolicyBlocked, evaluate
from mcias.palermo2 import verify

def policy(**overrides):
    d=dict(policy_id="signed-fixture-v1",currency="YER",rounding="HALF_UP",
        precision=2,order=("exclusion","tariff","cap","copay"),
        copay_percent=Decimal("20"),cap=Decimal("80"),
        exclusion=Decimal("10"),tariff=Decimal("100"),approved=True)
    d.update(overrides)
    return AuditPolicy(**d)

def calculate(p=None,**kwargs):
    return evaluate(Decimal("200"),"YER",p or policy(),eligible=True,
        evidence_complete=True,source_id="source-1",contract_id="contract-1",
        beneficiary_enrollment_id="enrollment-1",**kwargs)

def test_t08_combined_deductions_never_double_charge():
    result=calculate()
    assert [x["deduction"] for x in result["deductions"]]==["10.00","90.00","20.00","16.00"]
    assert result["total_deduction"]=="136.00"
    assert result["payable"]=="64.00"
    assert sum((Decimal(x["deduction"]) for x in result["deductions"]),Decimal(0))+Decimal(result["payable"])==Decimal("200")

def test_t08_deductions_cannot_exceed_claim():
    result=calculate(policy(exclusion=Decimal("500"),cap=Decimal("0"),tariff=Decimal("0")))
    assert result["total_deduction"]=="200.00"
    assert result["payable"]=="0.00"

@pytest.mark.parametrize("change",[
    {"approved":False},{"rounding":"UNDEFINED"},
    {"order":("tariff","exclusion","cap","copay")},
    {"copay_percent":Decimal("101")},{"cap":Decimal("-1")},
    {"exclusion":Decimal("NaN")}])
def test_g5_policy_fail_closed(change):
    with pytest.raises(PolicyBlocked):
        calculate(policy(**change))

def test_g5_missing_evidence_never_generates_deduction():
    result=evaluate(Decimal("200"),"YER",policy(),eligible=True,
        evidence_complete=False,source_id="source-1",contract_id="contract-1",
        beneficiary_enrollment_id="enrollment-1")
    assert result["status"]=="held" and result["deductions"]==[] and result["payable"] is None

def test_g5_currency_mismatch_blocks():
    with pytest.raises(PolicyBlocked,match="currency"):
        evaluate(Decimal("100"),"USD",policy(),eligible=True,evidence_complete=True,
            source_id="source-1",contract_id="contract-1",beneficiary_enrollment_id="enrollment-1")

def test_t09_palermo2_independently_detects_tampering():
    result=calculate()
    claim=SimpleNamespace(id="claim-1",claimed_amount=Decimal("200"),currency="YER",
        extracted_record_id="source-1")
    findings=[{"agent":x,"status":"pass"} for x in
        ("eligibility","tariff","contract","exclusion","caps","cost_sharing","duplicates","evidence")]
    assert verify(claim,findings,result)["status"]=="verified"
    modified={**result,"payable":"65.00"}
    assert "T09_financial_reconciliation_failed" in verify(claim,findings,modified)["issues"]
    assert verify(claim,[*findings[:-1],{"agent":"evidence","status":"hold"}],result)["status"]=="held"

def test_g5_reproducible_fingerprint():
    assert calculate()["fingerprint"]==calculate()["fingerprint"]

def test_t09_palermo2_detects_forged_fingerprint():
    result=calculate()
    claim=SimpleNamespace(id="claim-1",claimed_amount=Decimal("200"),currency="YER",
        extracted_record_id="source-1")
    findings=[{"agent":x,"status":"pass"} for x in
        ("eligibility","tariff","contract","exclusion","caps","cost_sharing","duplicates","evidence")]
    forged={**result,"payable":"65.00"}
    outcome=verify(claim,findings,forged)
    assert "calculation_fingerprint_mismatch" in outcome["issues"]
    assert outcome["status"]=="held"

def test_g5_unapproved_policy_blocks_even_missing_evidence():
    with pytest.raises(PolicyBlocked):
        evaluate(Decimal("100"),"YER",policy(approved=False),
            eligible=False,evidence_complete=False,source_id="src",
            contract_id="contract",beneficiary_enrollment_id="enrollment")
