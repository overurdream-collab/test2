"""G5 adversarial and property tests: no over-deduction, no implicit activation."""
from decimal import Decimal
from types import SimpleNamespace
import random
import pytest
from mcias.audit_engine import AuditPolicy,PolicyBlocked,evaluate
from mcias.audit_service import run_audit
from mcias.palermo2 import verify

def policy(exclusion,tariff,cap,copay):
    return AuditPolicy("synthetic-only","YER","HALF_UP",2,
        ("exclusion","tariff","cap","copay"),Decimal(str(copay)),
        Decimal(str(cap)),Decimal(str(exclusion)),Decimal(str(tariff)),True)

def test_t08_deterministic_1000_synthetic_financial_combinations():
    rng=random.Random(20261010)
    agents=[{"agent":n,"status":"pass"} for n in
        ("eligibility","tariff","contract","exclusion","caps","cost_sharing","duplicates","evidence")]
    for index in range(1000):
        claimed=Decimal(rng.randrange(0,200000))/100
        p=policy(rng.randrange(0,2000)/100,rng.randrange(0,200000)/100,
            rng.randrange(0,200000)/100,rng.randrange(0,101))
        result=evaluate(claimed,"YER",p,eligible=True,evidence_complete=True,
            source_id="record",contract_id="contract",beneficiary_enrollment_id="enrollment")
        deductions=[Decimal(s["deduction"]) for s in result["deductions"]]
        payable=Decimal(result["payable"])
        assert payable>=0
        assert all(x>=0 for x in deductions)
        assert sum(deductions,Decimal(0))+payable==claimed
        claim=SimpleNamespace(id=str(index),claimed_amount=claimed,currency="YER",
            extracted_record_id="record")
        assert verify(claim,agents,result)["status"]=="verified"

def test_g5_internal_service_denies_unsigned_policy_before_database_access():
    actor=SimpleNamespace(id="actor",organization_id="org",active=True)
    with pytest.raises(PolicyBlocked,match="verified institutional"):
        run_audit(None,actor,"claim",policy(0,100,100,0))
