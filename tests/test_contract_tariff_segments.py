"""C33 exact-source span isolation and tamper resistance; never model-derived gold."""
import json
from pathlib import Path
from hashlib import sha256
from mcias.contract_intelligence import validate_candidates
from scripts.contract_tariff_segments import isolated_tariff_blocks
CASES=json.loads((Path(__file__).parent/"fixtures"/"contract_independent_synthetic.json").read_text(encoding="utf-8"))

def test_two_provider_clauses_have_exact_anchored_nonoverlapping_spans():
    case=next(c for c in CASES if c["id"]=="NEW-MIXED-PROVIDERS")
    batches=isolated_tariff_blocks(case)
    assert len(batches)==2
    assert [b[0]["fields"]["text"] for b in batches]==[
        "Provider R3 CONSULT 4100 YER from 2026-01-01 until 2027-01-01.",
        "Provider R4 XRAY 8200 YER from 2026-01-01 until 2027-01-01."]
    for batch in batches:
        item=batch[0]
        start,end=item["locator"]["source_start"],item["locator"]["source_end"]
        assert case["source"][start:end]==item["fields"]["text"]
        assert item["record_id"]==case["id"]

def test_no_partition_if_price_missing_or_ambiguous_identity():
    case=next(c for c in CASES if c["id"]=="NEW-MIXED-PROVIDERS")
    for altered in [case["source"].replace("4100 YER","YER"),
                    case["source"].replace("Provider R4","Provider R3").replace("XRAY","CONSULT"),
                    case["source"].replace("Provider R4","WARNING Provider R4")]:
        assert len(isolated_tariff_blocks({**case,"source":altered}))==1
    for c in CASES:
        if c["id"]!=case["id"]:assert len(isolated_tariff_blocks(c))==1

def test_swapped_or_fabricated_amount_and_other_provider_remain_quarantined():
    case=next(c for c in CASES if c["id"]=="NEW-MIXED-PROVIDERS")
    b3,b4=isolated_tariff_blocks(case)
    def proposal(block,amount,provider,service,quote=None):
        return {"record_id":case["id"],"quote":quote or block[0]["fields"]["text"],
            "section":"tariffs","rule_type":"amount","provider_code":provider,
            "service_code":service,"logical_key":provider+":"+service,"amount":amount,
            "currency":"YER","effective_from":"2026-01-01","effective_until":"2027-01-01"}
    cases=[(b3,proposal(b3,"8200","R3","CONSULT"),"numeric_not_in_source"),
           (b4,proposal(b4,"4100","R4","XRAY"),"numeric_not_in_source"),
           (b3,proposal(b3,"1500","R3","CONSULT"),"numeric_not_in_source"),
           (b3,proposal(b3,"4100","R4","CONSULT"),"provider_not_in_source"),
           (b3,proposal(b3,"4100","R3","XRAY"),"service_not_in_source")]
    for blocks,p,error in cases:
        out=validate_candidates([p],blocks,source_sha256=sha256(case["source"].encode()).hexdigest(),model_id="SYN",model_revision="C33")[0]
        assert error in out["validation_errors"],(error,out)
        assert out["evidence_status"]=="needs_human_review"
    for blocks,amt,pro,svc in [(b3,"4100","R3","CONSULT"),(b4,"8200","R4","XRAY")]:
        out=validate_candidates([proposal(blocks,amt,pro,svc)],blocks,source_sha256=sha256(case["source"].encode()).hexdigest(),model_id="SYN",model_revision="C33")[0]
        assert out["validation_errors"]==[]
        assert out["evidence_status"]=="verified_source_anchor"
