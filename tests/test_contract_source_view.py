"""C35 deterministic-only source view, no Qwen, no new candidates."""
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from mcias.contract_intelligence import make_source_blocks, validate_candidates, ContractExtractionError
from mcias.contract_source_view import make_source_view, lookup_source_field
from scripts.contract_tariff_segments import isolated_tariff_blocks

CASES = json.loads((Path(__file__).parent / "fixtures" / "contract_independent_synthetic.json").read_text())
DIGEST = sha256(b"c35 frozen synthetic source").hexdigest()


def blocks(case):
    if case["id"] == "NEW-MIXED-PROVIDERS":
        return [part[0] for part in isolated_tariff_blocks(case)]
    return make_source_blocks([{"id": case["id"], "locator": case.get("locator", {"kind": "page", "index": 1}),
                                "values": case.get("values", {"text": case["source"]})}])


def test_r1_to_r6_literal_roundtrip_stability_and_no_mutation():
    for case in CASES:
        original = blocks(case)
        snapshot = deepcopy(original)
        view = make_source_view(original, source_sha256=DIGEST)
        assert view == make_source_view(deepcopy(original), source_sha256=DIGEST)
        assert original == snapshot
        assert len({f["id"] for f in view["fields"]}) == len(view["fields"])
        for field in view["fields"]:
            record = next(b for b in original if b["record_id"] == field["record_id"]
                          and b["locator"] == field["source_locator"])
            assert field["value"] == record["fields"][field["field_name"]]
            assert field["source_sha256"] == DIGEST
            assert lookup_source_field(view, field["id"]) == field
            assert field["locator"]["field"] == field["field_name"]
        with pytest.raises(ContractExtractionError):
            lookup_source_field(view, "f_nonexistent")


def test_provider_segment_and_sheet_row_boundaries():
    mixed = next(c for c in CASES if c["id"] == "NEW-MIXED-PROVIDERS")
    view = make_source_view(blocks(mixed), source_sha256=DIGEST)
    assert len(view["fields"]) == 2
    assert len({f["id"] for f in view["fields"]}) == 2
    assert len({f["group_id"] for f in view["fields"]}) == 2
    assert all(f["source_locator"]["source_start"] < f["source_locator"]["source_end"] for f in view["fields"])
    sheet = [c for c in CASES if c["id"].startswith("NEW-SHEET")]
    both = [blocks(c)[0] for c in sheet]
    v = make_source_view(both, source_sha256=DIGEST)
    assert len({f["group_id"] for f in v["fields"]}) == 2
    assert len({f["id"] for f in v["fields"]}) == len(v["fields"])
    assert {f["value"] for f in v["fields"] if f["field_name"] == "price"} == {"12000", "650.00"}
    assert all("YER" not in f["value"] for f in v["fields"] if f["field_name"] == "price")
    assert {f["source_locator"]["row"] for f in v["fields"]} == {5, 6}


def test_blank_repeated_numeric_ambiguous_and_cell_identity():
    records = [
        {"id": "doc", "locator": {"kind": "sheet", "index": 1, "row": 9},
         "values": {"A9": "  ", "B9": "500", "C9": "500", "D9": "5OO"}},
        {"id": "doc", "locator": {"kind": "sheet", "index": 1, "row": 10},
         "values": {"B10": "500", "C10": "YER"}},
    ]
    b = make_source_blocks(records)
    v = make_source_view(b, source_sha256=DIGEST)
    assert len(v["fields"]) == 5
    assert len({f["id"] for f in v["fields"]}) == 5
    assert [f["value"] for f in v["fields"]] == ["500", "500", "5OO", "500", "YER"]
    assert {f["locator"]["field"] for f in v["fields"]} == {"B9", "C9", "D9", "B10", "C10"}
    assert v["fields"][0]["group_id"] == v["fields"][1]["group_id"]
    assert v["fields"][0]["group_id"] != v["fields"][3]["group_id"]


def test_reject_duplicate_record_locator_missing_row_and_invalid_reference():
    row = {"record_id": "a", "locator": {"kind": "sheet", "index": 1, "row": 1},
           "fields": {"price": "100"}}
    for data in [[row, deepcopy(row)],
                 [{"record_id": "a", "locator": {"kind": "sheet", "index": 1}, "fields": {"price": "100"}}],
                 [{"record_id": "a", "locator": {"kind": "page", "index": True}, "fields": {"text": "x"}}]]:
        with pytest.raises(ContractExtractionError):
            make_source_view(data, source_sha256=DIGEST)
    with pytest.raises(ContractExtractionError):
        make_source_view([row], source_sha256="wrong")


def test_original_validator_unchanged_and_no_candidate_created():
    case = next(c for c in CASES if c["id"] == "NEW-SHEET-R5")
    original = blocks(case)
    view = make_source_view(original, source_sha256=DIGEST)
    assert "candidates" not in view
    raw = {"record_id": case["id"], "quote": "12000 YER", "section": "tariffs",
           "rule_type": "amount", "provider_code": "R5", "service_code": "MRI",
           "logical_key": "R5:MRI", "amount": "12000", "currency": "YER",
           "effective_from": "2026-01-01", "effective_until": "2027-01-01"}
    def verify():
        return validate_candidates([raw], original, source_sha256=DIGEST,
                                   model_id="C35-TEST", model_revision="NO-MODEL")[0]
    before = verify()
    _ = view
    after = verify()
    assert before == after
    assert "quote_not_in_source" in after["validation_errors"]
    assert after["evidence_status"] == "needs_human_review"
