"""Synthetic, deterministic gate tests for temporal clauses and four outputs."""
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace as Row
import pytest
from mcias.reference_points import _validate, PointConflict, MAX_DATE, SECTIONS
from mcias.claim_outcomes import (
    classify, classify_claims, export_csv, summarize, KINDS, ACCEPTED, REJECTED, REVIEW, MISSING
)


def point(**overrides):
    value = {"section": "tariffs", "logical_key": "HOSP-A:CONSULT",
        "title": "Consultation price", "clause_text": "Price agreed in signed annex",
        "rule_type": "amount", "provider_code": "HOSP-A", "service_code": "CONSULT",
        "amount": Decimal("5000.00"), "currency": "YER",
        "effective_from": date(2026, 1, 1), "effective_until": MAX_DATE}
    value.update(overrides)
    return value


def test_every_input_section_is_available():
    assert {"contracts", "providers", "beneficiaries", "cost_sharing",
            "categories", "exclusions", "approvals", "tariffs"} == SECTIONS


def test_provider_specific_tariffs_must_have_consistent_keys():
    _validate(point())
    _validate(point(logical_key="HOSP-B:CONSULT", provider_code="HOSP-B",
                    amount=Decimal("7000")))
    with pytest.raises(PointConflict):
        _validate(point(logical_key="HOSP-B:CONSULT"))
    with pytest.raises(PointConflict):
        _validate(point(currency="US"))


def test_invalid_value_or_dates_fail_closed():
    for kwargs in ({"amount": Decimal("NaN")},
                   {"amount": Decimal("-1")},
                   {"effective_from": MAX_DATE},
                   {"rule_type": "percentage", "amount": Decimal("101"), "section": "cost_sharing"}):
        with pytest.raises(PointConflict):
            _validate(point(**kwargs))


def findings(status="pass"):
    names = ("eligibility", "contract", "tariff", "exclusion",
             "caps", "cost_sharing", "duplicates", "evidence")
    return {"agents": [{"agent": name, "status": status} for name in names]}


def test_all_four_classification_branches():
    f = findings()
    assert classify(f, {"status": "verified"}, {"status": "calculated"})[0] == ACCEPTED
    f["agents"][-1]["status"] = "hold"
    assert classify(f, {"status": "held"}, {"status": "held"})[0] == MISSING
    f["agents"][-1]["status"] = "pass"
    f["agents"][0]["status"] = "hold"
    assert classify(f, {}, {})[0] == REVIEW
    # A mere missing enrollment is not a documented definite refusal.
    f["agents"][0]["status"] = "fail_confirmed"
    f["agents"][0]["evidence_confirmed"] = True
    f["agents"][0]["source_reference"] = "authoritative-registry:version-1"
    assert classify(f, {}, {})[0] == REJECTED
    del f["agents"][0]["source_reference"]
    assert classify(f, {}, {})[0] == REVIEW


def test_four_files_are_exclusive_and_excel_safe():
    claims = [
        Row(id="1", organization_id="org", claim_reference="=SUM(1,2)",
            provider_code="H-A", service_date=date(2026, 6, 1),
            claimed_amount=Decimal("100.0000"), currency="YER"),
        Row(id="2", organization_id="org", claim_reference="safe",
            provider_code="H-B", service_date=date(2026, 7, 1),
            claimed_amount=Decimal("200.0000"), currency="YER"),
    ]
    snap = Row(id="snap", organization_id="org", claim_id="1",
               created_at=datetime.now(timezone.utc), policy_fingerprint="abc",
               findings=findings(), verification={"status": "verified"},
               calculation={"status": "calculated"})
    rows = classify_claims(claims, [snap])
    assert summarize(rows)["total"] == 2
    assert summarize(rows)["counts"][ACCEPTED] == 1
    assert summarize(rows)["counts"][REVIEW] == 1
    assert sum(len([r for r in rows if r["outcome"] == k]) for k in KINDS) == 2
    data = export_csv(rows, ACCEPTED).decode("utf-8-sig")
    assert "'=SUM(1,2)" in data
    assert data.count("\n") == 2


def test_snapshot_tenant_mismatch_denied():
    claim = Row(id="1", organization_id="org", claim_reference="1", provider_code="p",
                service_date=date(2026, 1, 1), claimed_amount=Decimal(10), currency="USD")
    snap = Row(claim_id="1", organization_id="another")
    with pytest.raises(ValueError):
        classify_claims([claim], [snap])
