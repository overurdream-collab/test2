"""Independent synthetic fixtures: no model weights, private documents or external accounts."""
import json
from pathlib import Path
from scripts.contract_benchmark_scoring import count_matches
from mcias.contract_intelligence import make_source_blocks, validate_candidates
from hashlib import sha256

CASES = json.loads((Path(__file__).parent / "fixtures" / "contract_independent_synthetic.json").read_text(encoding="utf-8"))

def test_corpus_independent_and_bilingual():
    assert len(CASES) == 6
    assert all(x["id"].startswith("NEW-") for x in CASES)
    assert len([x for x in CASES if x["gold"]]) == 5
    assert len([x for x in CASES if x.get("locator",{}).get("kind") == "sheet"]) == 2
    assert any("تعرفة" in x["source"] for x in CASES)
    assert any("Provider" in x["source"] for x in CASES)
    assert any(len(x["gold"]) == 2 for x in CASES)
    assert count_matches({("tariffs","R2:XRAY","910")},{("tariffs","R2:XRAY","910.00")}) == (1,0,0)

def test_unverified_sheet_identity_and_amount_are_quarantined():
    case=next(x for x in CASES if x["id"] == "NEW-SHEET-R5")
    blocks=make_source_blocks([{"id":case["id"],"locator":case["locator"],"values":case["values"]}])
    proposal={"record_id":case["id"],"quote":"12000","section":"tariffs","logical_key":"R5:MRI",
        "rule_type":"amount","amount":"12000","provider_code":"R5","service_code":"MRI",
        "currency":"YER","effective_from":"2026-01-01","effective_until":"2027-01-01"}
    for k,v in (("provider_code","R6"),("service_code","XRAY"),("amount","12001")):
        fake=dict(proposal);fake[k]=v
        out=validate_candidates([fake],blocks,source_sha256=sha256(case["source"].encode()).hexdigest(),
                                model_id="SYN",model_revision="SYN")[0]
        assert out["validation_errors"],(k,out)
        assert out["evidence_status"] == "needs_human_review"
