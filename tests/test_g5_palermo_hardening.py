"""G5 regression: malformed data cannot become a verified payment or crash Palermo-2."""
from decimal import Decimal
from types import SimpleNamespace
from mcias.audit_engine import AuditPolicy, evaluate
from mcias.palermo2 import verify
from mcias.audit_agents import AGENTS

def _base():
    policy = AuditPolicy(policy_id="synthetic", currency="YER", precision=2,
        rounding="HALF_UP", order=("exclusion","tariff","cap","copay"),
        copay_percent=Decimal("0"), cap=None, exclusion=Decimal("0"),
        tariff=Decimal("100"), approved=True)
    claim = SimpleNamespace(id="c", claimed_amount=Decimal("100"),
        currency="YER", extracted_record_id="s")
    calc = evaluate(Decimal("100"),"YER",policy,eligible=True,
        evidence_complete=True,source_id="s",contract_id="contract",
        beneficiary_enrollment_id="member")
    findings = [{"agent":name,"status":"pass"} for name in AGENTS]
    return claim, calc, findings

def test_g5_valid_evidence_verified():
    claim, calc, findings = _base()
    assert verify(claim, findings, calc)["status"] == "verified"

def test_g5_nan_infinity_and_malformed_amounts_held_without_exception():
    claim, calc, findings = _base()
    for bad in ("NaN", "Infinity", "-Infinity", "garbage", None):
        tampered = {**calc, "payable": bad}
        outcome = verify(claim, findings, tampered)
        assert outcome["status"] == "held"
        assert "invalid_monetary_values" in outcome["issues"]

def test_g5_forged_deduction_total_and_wrong_agent_held():
    claim, calc, findings = _base()
    assert "deduction_total_mismatch" in verify(
        claim, findings, {**calc, "total_deduction":"999"})["issues"]
    malformed = [{"agent":"unrecognized","status":"pass"} for _ in AGENTS]
    assert "missing_or_duplicate_agent" in verify(claim, malformed, calc)["issues"]

def test_g5_missing_and_malformed_steps_fail_closed():
    claim, calc, findings = _base()
    for bad in (None, [{"deduction":"x"}], ["nonsense"]):
        result = verify(claim, findings, {**calc,"deductions":bad})
        assert result["status"] == "held"
