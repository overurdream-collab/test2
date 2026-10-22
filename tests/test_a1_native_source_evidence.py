"""A1 producer contract checks; native scope stub is NOT PG16 acceptance."""
from copy import deepcopy
import pytest
from sqlalchemy import JSON, bindparam, text

from mcias import claim_batches
from mcias.models_ingestion import ExtractedSourceRecord
from mcias.agents import invoice_integrity
from mcias.agents.a1_trusted_input import A1SourceBlocked, build_a1_snapshot, preview_a1_from_g4
from tests.test_a1_trusted_input import _setup, _claim


def _native_scope(db, claim, doc):
    # Emulate the return of the EXISTING server scope verifier. The independent
    # PG16 run must exercise the real approval path; this only checks A1's gate.
    record = db.get(ExtractedSourceRecord, claim.extracted_record_id)
    scope = {"approval_id": "SYN-scope", "mapping_version": "g4-canonical-v1",
             "source_sha256": doc.sha256, "job_id": record.job_id,
             "eligible_record_ids": [record.id], "excluded_record_ids": []}
    locator = {**record.locator, "document_id": doc.id, "job_id": record.job_id,
               "source_sha256": doc.sha256, "source_scope_approval_id": "SYN-scope",
               "mapping_version": "g4-canonical-v1", "sheet_type": "CLAIMS"}
    db.execute(text("UPDATE claim_entries SET source_locator = :locator WHERE id = :id")
               .bindparams(bindparam('locator', type_=JSON)),
               {"locator": locator, "id": claim.id})
    db.commit()
    db.expire_all()
    return scope


def test_native_lineage_keeps_metadata_and_source_field_evidence(tmp_path, monkeypatch):
    engine, db, store, org, actor = _setup(tmp_path)
    try:
        claim, doc, invoice = _claim(db, store, org, actor)
        scope = _native_scope(db, claim, doc)
        calls = []
        def verify(actual_db, actual_actor, document_id):
            calls.append(document_id)
            assert actual_db is db and actual_actor is actor and document_id == doc.id
            return scope
        monkeypatch.setattr(claim_batches, "source_scope", verify, raising=False)
        # The G5 consumer can rebuild source evidence without running A1 analysis.
        monkeypatch.setattr(invoice_integrity, "analyze", lambda *a, **kw: pytest.fail("analysis executed"))
        data = build_a1_snapshot(db, actor, claim.id, store, run_id="SYN-native")
        evidence = data["source_evidence"]
        assert calls == [doc.id]
        assert evidence["claim"]["source_record_id"] == claim.extracted_record_id
        assert evidence["claim"]["source_file_id"] == doc.source_id
        assert evidence["claim"]["source_scope"]["approval_id"] == "SYN-scope"
        assert evidence["claim"]["source"]["sha256"] == doc.sha256
        assert evidence["claim"]["provider_code"] == "H1"
        assert evidence["claim"]["service_date"] == "2026-06-30"
        line = evidence["invoice_lines"][0]
        assert (line["quantity"], line["unit_price"], line["line_total"], line["unit"], line["currency"]) == ("2", "10", "20", "visit", "YER")
        assert line["source_file_id"] == invoice.source_id
        assert line["field_sources"]["unit_price"] == {
            "source_file_id": invoice.source_id, "source_record_id": line["source_record_id"],
            "document_id": invoice.id, "sha256": invoice.sha256,
            "locator": "csv:row:2:field:unit_price"}
        assert evidence["arithmetic_qualification"]["source_qualified"] is True
        assert evidence["arithmetic_qualification"]["qualified"] is False
        assert data["source_evidence_fingerprint"] == invoice_integrity.digest(evidence)
        changed = deepcopy(evidence)
        changed["invoice_lines"][0]["unit_price"] = "999"
        assert invoice_integrity.digest(changed) != data["source_evidence_fingerprint"]
    finally:
        db.close(); engine.dispose()


@pytest.mark.parametrize("mutation", ["row", "document", "job", "hash", "approval", "version", "payment", "excluded", "stripped"])
def test_native_scope_or_location_substitution_is_blocked(tmp_path, monkeypatch, mutation):
    engine, db, store, org, actor = _setup(tmp_path)
    try:
        claim, doc, _ = _claim(db, store, org, actor)
        scope = _native_scope(db, claim, doc)
        locator = dict(claim.source_locator)
        changes = {"row": ("row", 3), "document": ("document_id", "SYN-other"),
                   "job": ("job_id", "SYN-other"), "hash": ("source_sha256", "0" * 64),
                   "approval": ("source_scope_approval_id", "SYN-other"),
                   "version": ("mapping_version", "SYN-other"), "payment": ("sheet_type", "PAYMENT")}
        if mutation == "excluded":
            scope["excluded_record_ids"] = [claim.extracted_record_id]
        elif mutation == "stripped":
            locator = {k: locator[k] for k in ("kind", "index", "row", "column")}
        else:
            name, value = changes[mutation]
            locator[name] = value
        db.execute(text("UPDATE claim_entries SET source_locator = :locator WHERE id = :id")
                   .bindparams(bindparam('locator', type_=JSON)),
                   {"locator": locator, "id": claim.id})
        db.commit(); db.expire_all()
        monkeypatch.setattr(claim_batches, "source_scope", lambda *a: scope, raising=False)
        with pytest.raises(A1SourceBlocked, match="native_claim_source_scope_mismatch"):
            build_a1_snapshot(db, actor, claim.id, store, run_id="SYN-blocked")
    finally:
        db.close(); engine.dispose()


def test_review_packet_evidence_copy_is_bound_without_financial_authority(tmp_path):
    engine, db, store, org, actor = _setup(tmp_path)
    try:
        claim, _, _ = _claim(db, store, org, actor)
        preview = preview_a1_from_g4(db, actor, claim.id, store, run_id="SYN-review")
        packet = preview["review_packet"]
        assert packet["tenant_id"] == org.id and packet["claim_id"] == claim.id
        assert packet["source_evidence_fingerprint"] == invoice_integrity.digest(packet["source_evidence"])
        assert packet["source_evidence"]["unit_price_authority"] == "NOT_ESTABLISHED"
        assert not packet["financial_decision_authorized"]
        assert packet["g7_realized_savings"] is None
        preview["source_evidence"]["invoice_lines"][0]["unit_price"] = "999"
        assert packet["source_evidence"]["invoice_lines"][0]["unit_price"] == "10"
    finally:
        db.close(); engine.dispose()
