"""Actual A1 source builder -> existing G5 -> Shared Audit/G6/G7, no AI.

Uses the existing native G2/G4/G3 fixture. Explicit arithmetic authority is
absent from this contract: even a readable invoice remains unresolved.
"""
from copy import deepcopy
import json
import os

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from mcias.agents.a1_trusted_input import (
    REQUIRED_FIELDS, REQUIRED_SENSITIVE, preview_a1_from_g4,
)
from mcias.agents.invoice_integrity import digest
from mcias.audit_service import run_audit
from mcias.claim_batches import attach
from mcias.governance_g6 import open_case, append_event
from mcias.models import AuditLog, Permission, Role, RolePermission
from mcias.models_audit import AuditSnapshot
from mcias.models_reporting_g7 import ReportSnapshot
from mcias.reporting_g7 import create_snapshot
from test_g5_inputs_first_review import (
    native_review, _claim, _references, _execution, _ingest, _csv,
)


def grant_source_field_reads(db):
    role = db.scalar(select(Role).where(Role.code == "super_admin"))
    for code in (*REQUIRED_FIELDS, *REQUIRED_SENSITIVE):
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code)
            db.add(permission)
            db.flush()
        if db.scalar(select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id,
        )) is None:
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
    db.commit()


@pytest.mark.parametrize("scenario", [
    "consistent_invoice", "conflicting_invoice", "rehashed_source_swap", "missing_store",
])
def test_original_invoice_packet_remains_advisory_and_durable(native_review, scenario):
    db, actor, store, engine = native_review
    grant_source_field_reads(db)
    claim, document, batch = _claim(db, actor, store)
    _references(db, actor, store, "match")
    _execution(db, actor, store, claim, "match")
    conflicting = scenario == "conflicting_invoice"
    row = {"line_item_id": "SYN-LINE-1", "service_code": claim.service_code,
        "unit": "UNIT", "currency": claim.currency,
        "quantity": "2" if conflicting else "1",
        "unit_price": "60" if conflicting else "100",
        "line_total": "110" if conflicting else "100",
        "invoice_total": "115" if conflicting else "100",
        "claim_reference": claim.claim_reference, "provider_code": claim.provider_code}
    invoice = _ingest(db, actor, store, "SYN-invoice.csv", _csv([row]))
    attach(db, actor, claim.id, invoice.id)
    preview = preview_a1_from_g4(db, actor, claim.id, store, run_id="SYN-NATIVE-A1-1")
    assert preview["financial_decision"] == "NOT_AUTHORIZED"
    packet = deepcopy(preview["review_packet"])
    line = packet["source_evidence"]["invoice_lines"][0]
    assert line["source"]["document_id"] == invoice.id
    assert line["source_record_id"] and line["field_sources"]["unit_price"]["source_record_id"]
    assert packet["source_evidence"]["claim"]["source_scope"]["sheet_type"] == "CLAIMS"
    if scenario == "rehashed_source_swap":
        line["unit_price"] = "999"
        packet["source_evidence_fingerprint"] = digest(packet["source_evidence"])
    snapshot = run_audit(db, actor, claim.id, review_only=True,
        a1_review_packet=packet, evidence_store=None if scenario == "missing_store" else store)
    check = next(item for item in snapshot.findings["agents"] if item["agent"] == "evidence")
    evidence = check["a1_evidence"]
    expected_gap = ("a1_packet_source_values_mismatch" if scenario == "rehashed_source_swap"
        else "source_verification_unavailable" if scenario == "missing_store"
        else "approved_arithmetic_rule_missing")
    assert snapshot.findings["audit_state"] == "UNRESOLVED"
    assert expected_gap in evidence["gaps"]
    assert evidence["source_evidence_verified"] is (scenario not in {"rehashed_source_swap", "missing_store"})
    assert evidence["a1_input_fingerprint_verified"] is False
    assert evidence["a1_output_fingerprint_verified"] is False
    codes = {item["code"] for item in evidence["signals"]}
    assert bool(codes) is conflicting
    if conflicting:
        assert "invoice_line_arithmetic_conflict" in codes
        assert "invoice_claim_amount_conflict" in codes
    assert snapshot.calculation["payable"] is None and snapshot.calculation["deductions"] == []
    retry_packet = packet
    if scenario == "consistent_invoice":
        # A real pipeline retry rebuilds its producer packet. A1's operational
        # timestamps may change its unverified hashes, but not the source facts.
        retry_packet = preview_a1_from_g4(db, actor, claim.id, store,
            run_id="SYN-NATIVE-A1-1")["review_packet"]
        assert retry_packet["source_evidence_fingerprint"] == packet["source_evidence_fingerprint"]
        assert retry_packet["a1_output_fingerprint"] != packet["a1_output_fingerprint"]
    repeated = run_audit(db, actor, claim.id, review_only=True,
        a1_review_packet=retry_packet, evidence_store=None if scenario == "missing_store" else store)
    assert repeated.id == snapshot.id
    events = db.scalars(select(AuditLog).where(AuditLog.action == "claim_inputs_audited")).all()
    assert len(events) == 1 and events[0].details["audit_snapshot_id"] == snapshot.id
    assert all(value not in json.dumps(events[0].details) for value in (
        claim.beneficiary_token, claim.claim_reference, claim.provider_code, "SYN-LINE-1"))
    case = open_case(db, actor, snapshot.id)
    hold = append_event(db, actor, case.id, "hold", {"reason_code": "advisory_human_review"})
    report = create_snapshot(db, actor, batch.id)
    reported = report.dataset["rows"][0]
    assert reported["audit_state"] == "UNRESOLVED" and reported["completed_audit"] is False
    assert reported["audit_event_ids"] == [events[0].id]
    assert reported["governance_event_id"] == hold.id
    assert report.summary["audit"]["incomplete_audit_count"] == 1
    assert create_snapshot(db, actor, batch.id).id == report.id
    db.commit()
    with Session(engine) as reread:
        durable = reread.get(AuditSnapshot, snapshot.id)
        assert durable.findings == snapshot.findings
        assert reread.get(ReportSnapshot, report.id).dataset == report.dataset
        assert reread.get(AuditLog, events[0].id).details["source_sha256"] == document.sha256
    output = os.getenv("MCIAS_A1_BRIDGE_EVIDENCE_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(json.dumps({"scenario": scenario, "database": engine.dialect.name,
                "expected": "UNRESOLVED", "actual": snapshot.findings["audit_state"],
                "claim_id": claim.id, "source_sha256": document.sha256,
                "invoice_document_id": invoice.id, "invoice_sha256": invoice.sha256,
                "snapshot_id": snapshot.id, "audit_event_id": events[0].id,
                "g6_case_id": case.id, "g6_hold_event_id": hold.id,
                "g7_report_id": report.id, "g7_fingerprint": report.fingerprint,
                "producer_packet_recreated": scenario == "consistent_invoice",
                "source_evidence_fingerprint": packet["source_evidence_fingerprint"],
                "original_a1_output_fingerprint": packet["a1_output_fingerprint"],
                "retry_a1_output_fingerprint": retry_packet["a1_output_fingerprint"],
                "retry_snapshot_id": repeated.id,
                "source_evidence_verified": evidence["source_evidence_verified"],
                "gaps": evidence["gaps"], "signal_codes": sorted(codes),
                "financial_decision": "not_authorized"}) + "\n")
