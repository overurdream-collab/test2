"""Native source-backed advisory E1; SQLite locally, isolated PG16 on request.

All records are synthetic and are produced by existing G2/G4/G3 services.
The optional output is a known-truth artifact, not a production acceptance.
"""
from datetime import date
from io import BytesIO, StringIO
from uuid import uuid4
import csv
import json
import os

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from mcias.audit_agents import canonical_audit_state, project_audit_findings
from mcias.audit_engine import PolicyBlocked
from mcias.audit_service import run_audit
from mcias.claim_batches import approve_source_scope, attach, stage, resume
from mcias.governance_g6 import open_case, append_event
from mcias.ingestion.orchestrator import ingest
from mcias.models import Base, AuditLog, Organization, Permission, Role, RolePermission, SourceFile, User, UserRole
from mcias.models_audit import AuditSnapshot
from mcias.models_claims import ClaimEntry
from mcias.models_ingestion import ExtractedSourceRecord, IngestionDocument, IngestionJob
from mcias.reference_service import register_reference_dataset, approve_reference_dataset
from mcias.storage import EncryptedStore


@pytest.fixture
def native_review(tmp_path):
    url = os.getenv("MCIAS_TEST_DATABASE_URL", "sqlite://")
    engine = create_engine(url)
    schema = None
    if os.getenv("MCIAS_TEST_DATABASE_URL"):
        assert engine.dialect.name == "postgresql"
        with engine.begin() as connection:
            assert 160000 <= int(connection.scalar(text("SHOW server_version_num"))) < 170000
            schema = "g5_review_" + uuid4().hex
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        isolated = engine.execution_options(schema_translate_map={None: schema})
    else:
        isolated = engine
    Base.metadata.create_all(isolated)
    store = EncryptedStore(str(tmp_path / "encrypted"), b"s" * 32)
    with Session(isolated, expire_on_commit=False) as db:
        org = Organization(name="SYN-REVIEW")
        db.add(org); db.flush()
        actor = User(organization_id=org.id, username="SYN-" + uuid4().hex, password_hash="synthetic")
        db.add(actor); db.flush()
        role = Role(code="super_admin")
        db.add(role); db.flush()
        db.add(UserRole(user_id=actor.id, role_id=role.id))
        for code in ("claims.read", "claims.import", "workspace.super_admin", "governance.review"):
            permission = Permission(code=code)
            db.add(permission); db.flush()
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        db.commit()
        yield db, actor, store, isolated
    if schema:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


def _csv(rows):
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
    return output.getvalue().encode()


def _ingest(db, actor, store, filename, data):
    result = ingest(db, store, actor.organization_id, actor.id, filename, data)
    assert result["status"] == "extracted", result
    document = db.get(IngestionDocument, result["document_id"])
    source = db.get(SourceFile, document.source_id)
    assert store.get(source.storage_key, source.sha256) == data
    return document


def _claim(db, actor, store, *, price="100", copay="20", service_date="2026-06-01"):
    row = {"claim_reference": "SYN-CLAIM", "beneficiary_token": "SYN-BEN", "provider_code": "SYN-PROVIDER",
        "service_code": "SYN-SERVICE", "service_date": service_date, "claimed_amount": price, "currency": "USD",
        "quantity": "1", "unit_price": price, "unit": "UNIT", "copay_amount": copay}
    book = Workbook(); sheet = book.active; sheet.title = "CLAIMS"
    sheet.append(list(row)); sheet.append(list(row.values()))
    payment = book.create_sheet("PAYMENT"); payment.append(list(row))
    payment.append(["SYN-PAYMENT" if key == "claim_reference" else value for key, value in row.items()])
    stream = BytesIO(); book.save(stream); book.close()
    document = _ingest(db, actor, store, "SYN-claims.xlsx", stream.getvalue())
    approve_source_scope(db, actor, document.id, {1: "CLAIMS", 2: "PAYMENT"})
    batch = stage(db, actor, document.id)
    result = resume(db, actor, batch.id)
    assert result["status"] == "imported"
    claims = db.scalars(select(ClaimEntry)).all()
    assert len(claims) == 1 and claims[0].claim_reference == "SYN-CLAIM"
    assert claims[0].source_locator["index"] == 1 and claims[0].source_locator["row"] == 2
    return claims[0], document, batch


def _facts(scenario):
    dates = {"effective_from": "2026-01-01", "effective_until": "2026-07-01"}
    values = {
        "beneficiary": {"beneficiary_token": "SYN-BEN", "employee_token": "SYN-EMP", "relationship": "self",
            "category_code": "SYN-CAT", "eligible": scenario != "eligibility_date", "covered_services": ["SYN-SERVICE"]},
        "contract": {"provider_code": "SYN-PROVIDER", "contract_key": "SYN-CONTRACT", "covered_services": ["SYN-SERVICE"], "excluded_services": []},
        "tariff": {"provider_code": "SYN-PROVIDER", "service_code": "SYN-SERVICE", "category_code": "SYN-CAT", "currency": "USD",
            "unit": "UNIT", "unit_price": "100", "price_basis": "unit_price",
            "price_comparison": "ceiling" if scenario == "ceiling_discount" else "exact"},
        "policy": {"service_code": "SYN-SERVICE", "category_code": "SYN-CAT", "currency": "USD", "copay_percent": "20",
            "requires_execution_evidence": True, "minimum_dispense_interval_days": None, "copay_basis": "claimed_amount",
            "rounding": "HALF_UP", "precision": 2, "duplicate_paid_claims_prohibited": True, "early_dispense_days": 2},
        "caps": {"beneficiary_token": "SYN-BEN", "category_code": "SYN-CAT", "service_code": "SYN-SERVICE", "currency": "USD",
            "limit_amount": "1000", "consumed_amount": "950" if scenario == "cap" else "0", "period_from": "2026-01-01",
            "period_until": "2026-07-01", "consumption_as_of": "2026-06-01", "consumed_excludes_current_claim": True,
            "consumption_basis": "claimed_amount"},
        "history": {"beneficiary_token": "SYN-BEN", "provider_code": "SYN-PROVIDER", "service_code": "SYN-OTHER",
            "service_date": "2026-05-01", "claim_reference": "SYN-OLD", "paid": True, "quantity": "1", "unit": "UNIT", "amount": "100", "currency": "USD"}}
    if scenario == "absent_incomplete":
        values["beneficiary"]["beneficiary_token"] = "SYN-OTHER-BEN"
    if scenario in {"duplicate", "legitimate_periodic", "future_history", "reference_collision", "missing_due"}:
        values["history"]["service_code"] = "SYN-SERVICE"
        values["history"]["next_dispense_due_date"] = "2026-06-01"
        if scenario in {"duplicate", "future_history", "reference_collision"}:
            values["history"]["claim_reference"] = "SYN-CLAIM"
            values["history"]["service_date"] = "2026-06-02" if scenario == "future_history" else "2026-06-01"
            if scenario == "reference_collision":
                values["history"]["quantity"] = "2"
    if scenario in {"legitimate_periodic", "missing_due"}:
        values["caps"]["consumed_amount"] = "100"
    if scenario == "missing_due":
        values["policy"]["minimum_dispense_interval_days"] = 30
        values["history"].pop("next_dispense_due_date")
    return {key: {**value, **dates} for key, value in values.items()}


def _references(db, actor, store, scenario):
    versions = []
    for family, value in _facts(scenario).items():
        rows = [{"record_key": "SYN-ROW", "payload": json.dumps(value)}]
        document = _ingest(db, actor, store, "SYN-" + family + ".csv", _csv(rows))
        item = register_reference_dataset(db, actor, document.id, family, dataset_key="SYN-" + family,
            version=1, effective_from=date(2026, 1, 1), effective_until=date(2026, 7, 1),
            coverage_from=date(2026, 1, 1), coverage_until=date(2026, 7, 1),
            scope={"provider_code": "SYN-PROVIDER", "all_beneficiaries": True, "all_services": True}, expected_record_count=1)
        if scenario != "absent_incomplete" or family != "beneficiary":
            approve_reference_dataset(db, actor, item.id, reason_code="source_scope_complete")
        versions.append(item)
    if scenario == "match":
        # A newer approved version must not replace the historical June price.
        value = {**_facts(scenario)["tariff"], "effective_from": "2026-07-01",
            "effective_until": "2027-01-01", "unit_price": "999"}
        document = _ingest(db, actor, store, "SYN-tariff-v2.csv", _csv([
            {"record_key": "SYN-ROW", "payload": json.dumps(value)}]))
        newer = register_reference_dataset(db, actor, document.id, "tariff", dataset_key="SYN-tariff",
            version=2, effective_from=date(2026, 7, 1), effective_until=date(2027, 1, 1),
            coverage_from=date(2026, 7, 1), coverage_until=date(2027, 1, 1),
            scope={"provider_code": "SYN-PROVIDER", "all_beneficiaries": True, "all_services": True}, expected_record_count=1)
        approve_reference_dataset(db, actor, newer.id, reason_code="source_scope_complete")
        versions.append(newer)
    return versions


def _execution(db, actor, store, claim, scenario):
    if scenario == "missing_execution":
        return None
    row = {"evidence_kind": "service_execution", "claim_reference": claim.claim_reference,
        "beneficiary_token": claim.beneficiary_token, "provider_code": claim.provider_code,
        "service_code": claim.service_code, "service_date": claim.service_date.isoformat(),
        "unit": "UNIT", "performed_quantity": "1", "dose_status": "clear"}
    if scenario == "invoice_prescription":
        row.update(evidence_kind="prescription", service_code="SYN-CONFLICT")
    elif scenario == "ambiguous_dose":
        row["dose_status"] = "ambiguous"
    document = _ingest(db, actor, store, "SYN-execution.csv", _csv([row]))
    attach(db, actor, claim.id, document.id)
    if scenario == "wrong_locator":
        # Fault injection: text/values remain correct, but an OCR page rectangle
        # cannot qualify this individual field. No approved original is edited.
        record = db.scalar(select(ExtractedSourceRecord).join(IngestionJob).where(IngestionJob.document_id == document.id))
        record.locator = {"kind": "page", "page": 1, "bbox": [0, 0, 1000, 1000]}
        db.commit()
    return document


CASES = [("match", "MATCH_VERIFIED"), ("tariff", "VIOLATION_PROVEN"), ("cap", "VIOLATION_PROVEN"),
    ("duplicate", "VIOLATION_PROVEN"), ("legitimate_periodic", "MATCH_VERIFIED"),
    ("eligibility_date", "VIOLATION_PROVEN"), ("absent_incomplete", "UNRESOLVED"),
    ("expired", "UNRESOLVED"), ("invoice_prescription", "UNRESOLVED"), ("ambiguous_dose", "UNRESOLVED"),
    ("missing_execution", "UNRESOLVED"), ("reimport", "MATCH_VERIFIED"), ("cross_org", "ACCESS_DENIED"),
    ("wrong_locator", "UNRESOLVED"), ("unreadable_source", "AUDIT_UNAVAILABLE"),
    ("copay", "VIOLATION_PROVEN"), ("discount_unapproved", "VIOLATION_PROVEN"), ("ceiling_discount", "MATCH_VERIFIED"),
    ("future_history", "MATCH_VERIFIED"), ("reference_collision", "UNRESOLVED"), ("missing_due", "UNRESOLVED")]


@pytest.mark.parametrize("scenario,expected", CASES)
def test_native_inputs_first_known_truth(native_review, tmp_path, scenario, expected):
    db, actor, store, engine = native_review
    claim, document, batch = _claim(db, actor, store,
        price="120" if scenario == "tariff" else "80" if scenario in {"discount_unapproved", "ceiling_discount"} else "100",
        copay="24" if scenario == "tariff" else "16" if scenario in {"discount_unapproved", "ceiling_discount"} else "0" if scenario == "copay" else "20",
        service_date="2027-01-01" if scenario == "expired" else "2026-06-01")
    references = _references(db, actor, store, scenario)
    _execution(db, actor, store, claim, scenario)
    if scenario == "unreadable_source":
        # Unreadability is a source status fault, not negative medical evidence.
        document.status = "failed"; db.commit()
    if scenario == "reimport":
        assert stage(db, actor, document.id).id == batch.id
        assert resume(db, actor, batch.id)["status"] == "imported"
        assert len(db.scalars(select(ClaimEntry)).all()) == 1
    if scenario == "cross_org":
        other = Organization(name="SYN-OTHER"); db.add(other); db.flush()
        outsider = User(organization_id=other.id, username="SYN-" + uuid4().hex, password_hash="synthetic")
        db.add(outsider); db.flush()
        role = db.scalar(select(Role).where(Role.code == "super_admin"))
        db.add(UserRole(user_id=outsider.id, role_id=role.id)); db.commit()
        with pytest.raises(PolicyBlocked, match="accessible"):
            run_audit(db, outsider, claim.id, review_only=True)
        assert db.scalar(select(AuditSnapshot)) is None
        evidence = {"case": scenario, "expected": expected, "actual": "ACCESS_DENIED", "claim_id": claim.id,
            "source_document_id": document.id, "event_id": None, "snapshot_id": None}
    else:
        snapshot = run_audit(db, actor, claim.id, review_only=True)
        assert snapshot.findings["audit_state"] == expected
        assert snapshot.findings["audit_state_schema_version"] == 2
        assert snapshot.calculation["status"] == "held" and snapshot.calculation["payable"] is None
        assert snapshot.calculation["deductions"] == [] and snapshot.verification["status"] == "held"
        assert run_audit(db, actor, claim.id, review_only=True).id == snapshot.id
        event = db.scalar(select(AuditLog).where(AuditLog.action == "claim_inputs_audited"))
        assert event.details["audit_snapshot_id"] == snapshot.id
        assert event.details["audit_state"] == expected
        assert len(db.scalars(select(AuditLog).where(AuditLog.action == "claim_inputs_audited")).all()) == 1
        assert all(token not in json.dumps(event.details) for token in ("SYN-BEN", "SYN-PROVIDER", "SYN-CLAIM"))
        with Session(engine) as reread:
            durable = reread.get(AuditSnapshot, snapshot.id)
            assert durable.findings == snapshot.findings
            assert reread.get(AuditLog, event.id).details == event.details
        case = open_case(db, actor, snapshot.id)
        hold = append_event(db, actor, case.id, "hold", {"reason_code": "advisory_human_review"})
        assert hold.kind == "hold"
        if scenario in {"missing_due", "reference_collision"}:
            duplicate_finding = next(item for item in snapshot.findings["agents"] if item["agent"] == "duplicates")
            assert duplicate_finding["audit_state"] == "UNRESOLVED" and duplicate_finding["reference"]
        if scenario == "match":
            tariff_certificate = next(item for item in snapshot.findings["reference_certificates"] if item["family"] == "tariff")
            assert tariff_certificate["version"] == 1 and references[-1].version == 2
        if scenario == "absent_incomplete":
            assert snapshot.findings["reason_code"] == "REFERENCE_INCOMPLETE"
            eligibility = next(item for item in snapshot.findings["agents"] if item["agent"] == "eligibility")
            assert eligibility["audit_state"] == "UNRESOLVED"
        evidence = {"case": scenario, "expected": expected, "actual": snapshot.findings["audit_state"],
            "claim_id": claim.id, "snapshot_id": snapshot.id, "event_id": event.id,
            "source_document_id": document.id, "source_sha256": document.sha256,
            "source_locator": claim.source_locator, "source_record_id": claim.extracted_record_id,
            "references": snapshot.findings["reference_certificates"], "findings": snapshot.findings["agents"],
            "governance_case_id": case.id, "human_hold_event_id": hold.id,
            "database": engine.dialect.name}
    output = os.getenv("MCIAS_E1_REVIEW_EVIDENCE_OUTPUT")
    if output:
        # Single-process suite writes one durable JSON line per successful case.
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(evidence, sort_keys=True) + "\n")
    (tmp_path / "expected_actual_evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")


def test_legacy_codec_is_read_only():
    old = {"audit_state": "VERIFIED_MATCH", "agents": [{"audit_state": "PROVEN_VIOLATION"}]}
    result = project_audit_findings(old)
    assert result["audit_state"] == "MATCH_VERIFIED" and result["agents"][0]["audit_state"] == "VIOLATION_PROVEN"
    assert old["audit_state"] == "VERIFIED_MATCH"
    assert result["source_audit_state_schema_version"] == 1
    assert project_audit_findings(result)["source_audit_state_schema_version"] == 1
    with pytest.raises(ValueError):
        canonical_audit_state("AUTO_APPROVE")


def test_reader_without_super_admin_cannot_persist_review(native_review):
    db, actor, store, engine = native_review
    claim, *_ = _claim(db, actor, store)
    reader = User(organization_id=actor.organization_id, username="SYN-reader", password_hash="synthetic")
    role = Role(code="SYN-reader")
    db.add_all([reader, role]); db.flush()
    permission = db.scalar(select(Permission).where(Permission.code == "claims.read"))
    db.add_all([UserRole(user_id=reader.id, role_id=role.id), RolePermission(role_id=role.id, permission_id=permission.id)])
    db.commit()
    with pytest.raises(PolicyBlocked, match="Super Admin"):
        run_audit(db, reader, claim.id, review_only=True)
    assert db.scalar(select(AuditSnapshot)) is None


@pytest.mark.parametrize("certificates,expected_reason", [
    (None, None), ([], None), ([{}], None), ([{"complete": None}], None),
    ([{"complete": True, "gaps": []}], None),
    ([{"complete": False}], "REFERENCE_INCOMPLETE"),
    ([{"gaps": ["reference_missing"]}], "REFERENCE_INCOMPLETE"),
])
def test_legacy_codec_does_not_invent_a_missing_reference_reason(certificates, expected_reason):
    from copy import deepcopy
    archived = {"audit_state": "UNRESOLVED_OR_MISSING_REFERENCE", "reference_certificates": certificates}
    original = deepcopy(archived)
    result = project_audit_findings(archived)
    assert result["audit_state"] == "UNRESOLVED"
    assert result["audit_state_schema_version"] == 2
    assert result["source_audit_state_schema_version"] == 1
    assert result.get("reason_code") == expected_reason
    assert archived == original
