"""E1 synthetic G2 parser -> CAI-01 source preflight boundary regression.

This does NOT invoke G4 persistence, G3, G5 or Shared Audit and is not E2E.
No owner-controlled implementation or database schema is modified.
"""
from io import BytesIO
from types import SimpleNamespace

from openpyxl import Workbook

from mcias.ingestion.parsers.excel_parser import parse
from mcias.claims_batch_preflight import inspect_extracted_records


def _synthetic_workbook():
    book = Workbook()
    claims = book.active
    claims.title = "CLAIMS"
    claims.append(["claim_reference", "beneficiary_token", "provider_code",
                   "service_code", "service_date", "claimed_amount", "currency"])
    claims.append(["SYN-CLAIM-001", "SYN-BEN-001", "SYN-PROV-001",
                   "SYN-SVC-001", "2026-09-15", "120.00", "USD"])
    payment = book.create_sheet("PAYMENT")
    payment.append(["payment_reference", "claim_reference", "payment_date",
                    "amount", "currency"])
    payment.append(["SYN-PAY-001", "SYN-CLAIM-001", "2026-09-16",
                    "90.00", "USD"])
    out = BytesIO()
    book.save(out)
    book.close()
    return out.getvalue()


def test_real_g2_parser_preflight_preserves_payment_provenance_without_claim_import():
    extraction = parse(_synthetic_workbook())
    assert extraction.format == "xlsx"
    assert extraction.units_total == 2
    assert extraction.units_processed == 2
    assert not extraction.quarantined
    assert len(extraction.records) == 2

    records = [
        SimpleNamespace(
            id=f"SYN-EXTRACT-{n}",
            locator={"kind": record.locator.kind,
                     "index": record.locator.index,
                     "row": record.locator.row},
            values=record.values,
        )
        for n, record in enumerate(extraction.records, start=1)
    ]
    # Explicit synthetic sheet selection is test input, NOT G2/G4 owner sign-off.
    result = inspect_extracted_records(
        records, claim_sheet_indices={1}, expected_records=2
    )
    assert result["status"] == "READY_FOR_G4"
    assert result["counts"]["source"] == 2
    assert result["counts"]["included"] == 1
    assert result["counts"]["excluded"] == 1
    assert result["counts"]["ready"] == 1
    assert result["row_outcomes"][0]["locator"] == {
        "kind": "sheet", "index": 1, "row": 2
    }
    assert result["row_outcomes"][1]["locator"] == {
        "kind": "sheet", "index": 2, "row": 2
    }
    assert result["row_outcomes"][1]["status"] == "EXCLUDED"
    assert result["semantics"] == "READ_ONLY_PREFLIGHT_NOT_FINANCIAL_AUDIT"


def test_real_g2_parser_cannot_authorize_sheet_without_explicit_scope():
    extraction = parse(_synthetic_workbook())
    records = [
        SimpleNamespace(id=f"SYN-{n}",
                        locator={"kind": r.locator.kind,
                                 "index": r.locator.index, "row": r.locator.row},
                        values=r.values)
        for n, r in enumerate(extraction.records, 1)
    ]
    result = inspect_extracted_records(records, expected_records=2)
    assert result["status"] == "BLOCKED"
    assert "CLAIM_SHEET_SELECTION_REQUIRED" in result["reason_codes"]
    assert result["counts"]["unscoped"] == 2
