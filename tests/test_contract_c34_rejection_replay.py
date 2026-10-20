"""C34 raw C33 rejection replay + literal-sheet negative safeguards (no model mocks as quality PASS)."""
import json
from hashlib import sha256
from pathlib import Path

from mcias.contract_intelligence import make_source_blocks, validate_candidates
from scripts.contract_tariff_segments import isolated_tariff_blocks

ROOT = Path(__file__).parent / "fixtures"
C33 = json.loads((ROOT / "contract_independent_synthetic.json").read_text(encoding="utf-8"))
C34 = json.loads((ROOT / "contract_c34_holdout_synthetic.json").read_text(encoding="utf-8"))


def _blocks(case):
    if case["id"] == "NEW-MIXED-PROVIDERS":
        return isolated_tariff_blocks(case)
    return [make_source_blocks([{"id": case["id"], "locator": case.get("locator", {"kind":"page","index":1}),
                                  "values":case.get("values", {"text":case["source"]})}])]


def _verify(case, candidate, blocks):
    return validate_candidates([candidate], blocks, source_sha256=sha256(case["source"].encode()).hexdigest(),
                               model_id="C33-REPLAY", model_revision="PINNED")[0]


def test_c33_real_raw_false_negatives_still_quarantined_by_unmodified_validator():
    mixed = next(x for x in C33 if x["id"] == "NEW-MIXED-PROVIDERS")
    r3, r4 = _blocks(mixed)
    raw_r3 = {"record_id": mixed["id"], "quote": "Provider R3 CONSULT 4100 YER from 2026-01-01 until 2027-01-01",
              "section":"tariffs","rule_type":"duration","provider_code":"R3","service_code":"CONSULT",
              "currency":None,"effective_from":"2026-01-01","effective_until":"2027-01-01",
              "amount":None,"logical_key":"provider_code:service_code"}
    raw_r4 = {"record_id": mixed["id"], "quote": "Provider R4 XRAY 8200 YER from 2026-01-01 until 2027-01-01",
              "section":"tariffs","rule_type":"amount","provider_code":"R4","service_code":"XRAY 8200",
              "currency":"YER","effective_from":"2026-01-01","effective_until":"2027-01-01",
              "amount":"150000","logical_key":"R4:XRAY 8200"}
    for blocks,raw,expected in [
        (r3,raw_r3,{"tariff_identity_incomplete"}),
        (r4,raw_r4,{"invalid_service","invalid_logical_key","numeric_not_in_source"})
    ]:
        output=_verify(mixed,raw,blocks)
        assert expected.issubset(set(output["validation_errors"])), output
        assert output["evidence_status"]=="needs_human_review"


def test_c33_real_raw_excel_quotes_not_in_single_source_cell():
    for case_id, quote, provider,service,amount in [
        ("NEW-SHEET-R5","12000 YER","R5","MRI","12000"),
        ("NEW-SHEET-R6","LAB 650.00 YER 2026-01-01 2027-01-01","R6","LAB","650.00")
    ]:
        case=next(x for x in C33 if x["id"]==case_id)
        raw={"record_id":case_id,"quote":quote,"section":"tariffs","rule_type":"amount",
             "provider_code":provider,"service_code":service,"logical_key":provider+":"+service,
             "amount":amount,"currency":"YER",
             "effective_from":"2026-01-01","effective_until":"2027-01-01"}
        actual=_verify(case,raw,_blocks(case)[0])
        assert "quote_not_in_source" in actual["validation_errors"]
        assert actual["evidence_status"]=="needs_human_review"
        literal=dict(raw,quote=case["values"]["price"])
        approved=_verify(case,literal,_blocks(case)[0])
        assert approved["validation_errors"]==[],approved
        altered=dict(literal,amount="999999")
        rejected=_verify(case,altered,_blocks(case)[0])
        assert "numeric_not_in_source" in rejected["validation_errors"]


def test_c34_holdout_distinct_and_source_validated():
    assert len(C34)==6 and sum(len(c["gold"]) for c in C34)==6
    assert {c["id"] for c in C33}.isdisjoint({c["id"] for c in C34})
    assert len([x for x in C34 if not x["gold"]])==1
    assert len(isolated_tariff_blocks(next(x for x in C34 if x["id"]=="C34-HOLDOUT-TWO-PROVIDERS")))==2
    for c in C34:
        if c.get("locator",{}).get("kind")=="sheet":
            p=c["values"]
            candidate={"record_id":c["id"],"quote":p["price"],"section":"tariffs",
                       "rule_type":"amount","provider_code":p["provider"],"service_code":p["service"],
                       "logical_key":p["provider"]+":"+p["service"],"amount":p["price"],
                       "currency":p["currency"],"effective_from":p["effective_from"],
                       "effective_until":p["effective_until"]}
            output=_verify(c,candidate,_blocks(c)[0])
            assert not output["validation_errors"],output
            invalid=dict(candidate,service_code="UNSOURCED")
            assert _verify(c,invalid,_blocks(c)[0])["evidence_status"]=="needs_human_review"
