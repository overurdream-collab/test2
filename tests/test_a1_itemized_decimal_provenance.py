"""Synthetic G2 encrypted original -> G4 -> A1 invoice arithmetic and provenance."""
import pytest
from mcias.models_claims import ClaimAttachment
from mcias.agents.a1_trusted_input import preview_a1_from_g4, build_a1_snapshot
from tests.test_a1_trusted_input import _setup, _claim, _document


@pytest.mark.parametrize("label,code,kind,qty,price,line_total,expected_type", [
    ("lab_valid", "LAB-CBC", "service", "2", "12.5000", "25.0000", None),
    ("medicine_qty_dispute", "MED-TAB", "service", "3", "7.00", "14.00", "LINE_ARITHMETIC"),
    ("consult_price_dispute", "CONSULT", "service", "2", "15.00", "20.00", "LINE_ARITHMETIC"),
    ("lab_total_dispute", "LAB-TEST", "service", "2", "10.25", "20.51", "LINE_ARITHMETIC"),
    ("medicine_missing_price", "MED-INJ", "service", "2", "", "20", None),
    ("administrative_fee", "ADMIN", "fee", "1", "5", "5", None),
])
def test_g2_g4_a1_decimal_source_cases(tmp_path, label, code, kind, qty, price, line_total, expected_type):
    engine, db, store, org, actor = _setup(tmp_path)
    try:
        # Every field, including an empty field, originates from one persisted,
        # hash-checked encrypted G2 CSV row; no invented OCR or tariff price.
        claim, _, _ = _claim(db, store, org, actor, invoice=False, amount=line_total)
        csv = (
            "line_item_id,service_code,unit,quantity,unit_price,line_total,"
            "invoice_total,claim_reference,provider_code,currency,item_kind\n"
            f"SYN-L1,{code},unit,{qty},{price},{line_total},"
            f"{claim.claim_reference},H1,YER,{kind}\n"
        ).encode()
        doc, rows = _document(db, store, org, label + ".csv", csv)
        db.add(ClaimAttachment(
            organization_id=org.id, claim_id=claim.id, ingestion_document_id=doc.id,
            document_sha256=doc.sha256, linked_by=actor.id))
        db.commit()
        state = build_a1_snapshot(db, actor, claim.id, store, run_id="SYN-" + label)
        preview = preview_a1_from_g4(db, actor, claim.id, store, run_id="SYN-preview-" + label)
        packet = preview["review_packet"]
        assert preview["financial_decision"] == "NOT_AUTHORIZED"
        assert packet["financial_decision_authorized"] is False
        assert packet["classification_is_final"] is False
        assert packet["provisional_four_way_code"] == "HUMAN_REVIEW"
        assert packet["g6_authorized_reviewer_decision"] == "PENDING"
        assert packet["g7_realized_savings"] is None
        assert state["snapshot"].contracts == []
        assert all(v.original_sha256_verified and v.extracted_rows_equal_original
                   for v in state["snapshot"].source_verifications)
        assert doc.sha256 in [v.sha256 for v in state["snapshot"].source_verifications]
        if label == "medicine_missing_price":
            assert not state["snapshot"].invoice.items
            assert "invalid_invoice_row" in preview["missing_evidence"]
            assert preview["a1"]["finding_status"] == "INSUFFICIENT_EVIDENCE"
            assert not any(f["finding_type"] == "LINE_ARITHMETIC"
                           for f in preview["a1"]["findings"])
        else:
            item = state["snapshot"].invoice.items[0]
            assert item.quantity == qty
            assert item.unit_price == price
            assert item.line_total == line_total
            assert item.source.document_id == doc.id
            assert item.source.sha256 == doc.sha256
            findings = [f for f in preview["a1"]["findings"]
                        if f["finding_type"] == "LINE_ARITHMETIC"]
            assert bool(findings) == bool(expected_type)
            if findings:
                assert findings[0]["finding_status"] == "REVIEW"
                assert any(r["document_id"] == doc.id and r["sha256"] == doc.sha256
                           for r in findings[0]["evidence_refs"])
        if kind == "fee":
            assert "approved_contract_fee_clause" in preview["missing_evidence"]
            assert "approved_contract_fee_clause" in packet["missing_evidence"]
            assert state["g3_reference"]["additional_fee_authority"] == "NOT_ESTABLISHED"
    finally:
        db.close()
        engine.dispose()
