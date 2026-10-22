"""Isolated INPUTS-FIRST source contract tests; no G4/G5/Shared Audit emulation."""
from types import SimpleNamespace
import pytest
from mcias.claims_batch_preflight import inspect_extracted_records

BASE = {
    "claim_reference": "SYN-001", "beneficiary_token": "SYN-PERSON",
    "provider_code": "SYN-PROVIDER", "service_code": "SYN-SERVICE",
    "service_date": "2026-10-20", "claimed_amount": "10.0000", "currency": "YER",
}

def source(i, sheet=1, values=None):
    return SimpleNamespace(id=f"SYN-{i}", locator={"kind":"sheet","index":sheet,"row":i+1},
                           values=dict(BASE, claim_reference=f"SYN-{i}") if values is None else values)

def test_no_worksheet_approval_is_blocked():
    result=inspect_extracted_records([source(1)],expected_records=1)
    assert result["status"]=="BLOCKED"
    assert "CLAIM_SHEET_SELECTION_REQUIRED" in result["reason_codes"]

def test_non_claim_sheets_excluded_not_deleted():
    records=[source(1,1),source(2,2,{"payment_total":"10"}),source(3,3,{"family_total":"10"})]
    result=inspect_extracted_records(records,claim_sheet_indices={1},expected_records=3)
    assert result["counts"]["excluded"]==2
    assert len(result["row_outcomes"])==3
    assert [r["status"] for r in result["row_outcomes"]]==["INCLUDED","EXCLUDED","EXCLUDED"]

def test_unknown_claim_sheet_blocks():
    result=inspect_extracted_records([source(1)],claim_sheet_indices={4})
    assert result["status"]=="BLOCKED"
    assert "UNKNOWN_CLAIM_SHEET" in result["reason_codes"]

def test_invalid_amount_held():
    result=inspect_extracted_records([source(1,values=dict(BASE,claimed_amount="NaN"))],claim_sheet_indices={1})
    assert result["status"]=="BLOCKED"
    assert result["row_outcomes"][0]["status"]=="HOLD_INVALID"

def test_incomplete_source_count_blocks():
    result=inspect_extracted_records([source(1)],claim_sheet_indices={1},expected_records=2)
    assert result["status"]=="BLOCKED"
    assert "SOURCE_COUNT_MISMATCH" in result["reason_codes"]

def test_duplicate_source_locator_blocks():
    records=[source(1),SimpleNamespace(id="SYN-DIFFERENT",locator={"kind":"sheet","index":1,"row":2},values=dict(BASE))]
    result=inspect_extracted_records(records,claim_sheet_indices={1})
    assert result["status"]=="BLOCKED"
    assert "DUPLICATE_SOURCE_ID_OR_LOCATOR" in result["reason_codes"]

def test_possible_semantic_duplicate_is_review_not_proven_violation():
    records=[source(1,values=dict(BASE,claim_reference="SYN-A")),
             source(2,values=dict(BASE,claim_reference="SYN-B"))]
    result=inspect_extracted_records(records,claim_sheet_indices={1})
    assert result["status"]=="REVIEW_REQUIRED"
    assert len(result["possible_duplicate_record_ids"])==1

def test_valid_source_row_not_a_financial_approval():
    result=inspect_extracted_records([source(1)],claim_sheet_indices={1},expected_records=1)
    assert result["status"]=="READY_FOR_G4"
    assert result["semantics"]=="READ_ONLY_PREFLIGHT_NOT_FINANCIAL_AUDIT"
    assert "financial_decision" not in result

@pytest.mark.parametrize("field,value",[
    ("service_date","not-a-date"),
    ("currency","NOT-A-CURRENCY"),
])
def test_invalid_normalization_is_held(field,value):
    result=inspect_extracted_records([source(1,values=dict(BASE,**{field:value}))],claim_sheet_indices={1})
    assert result["status"]=="BLOCKED"
    assert result["row_outcomes"][0]["status"]=="HOLD_INVALID"
