"""Real PG16 synthetic claim-audit correlation, rollback and atomic dedup.

Only a disposable localhost database named mcias_inputs_audit is accepted.
No Alembic migration, production connection or patient fixture is used.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import uuid4
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from mcias.audit_contract import REFERENCE_FAMILIES, clean_claim_audit_details
from mcias.audit_writer import write_event
from mcias.models import AuditLog, Base, Organization, SourceFile, User
from mcias.models_audit import AuditSnapshot
from mcias.models_claims import ClaimBatch, ClaimEntry
from mcias.models_ingestion import ExtractedSourceRecord, IngestionDocument, IngestionJob


@pytest.fixture
def engine():
    url = os.getenv("MCIAS_INPUTS_AUDIT_DATABASE_URL")
    if not url:
        pytest.skip("dedicated synthetic PostgreSQL16 fixture required")
    assert os.getenv("MCIAS_INPUTS_AUDIT_ALLOW") == "YES"
    parsed = urlsplit(url.replace("postgresql+psycopg://", "postgresql://", 1))
    assert parsed.hostname in {"localhost", "127.0.0.1"}
    assert parsed.path == "/mcias_inputs_audit"
    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.dialect.server_version_info[0] == 16
    tables = [Organization.__table__, User.__table__, SourceFile.__table__,
        IngestionDocument.__table__, IngestionJob.__table__, ExtractedSourceRecord.__table__,
        ClaimBatch.__table__, ClaimEntry.__table__, AuditSnapshot.__table__, AuditLog.__table__]
    assert all(not inspect(engine).has_table(table.name) for table in tables), "empty disposable DB required"
    Base.metadata.create_all(engine, tables=tables)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine, tables=list(reversed(tables)))
        engine.dispose()


def _seed(engine):
    with Session(engine) as db:
        org = Organization(name="SYN-INPUTS-AUDIT")
        db.add(org); db.flush()
        actor = User(organization_id=org.id, username="SYN-audit", password_hash="unused")
        source = SourceFile(sha256="a" * 64, original_filename="synthetic.xlsx", storage_key=str(uuid4()))
        db.add_all([actor, source]); db.flush()
        document = IngestionDocument(organization_id=org.id, source_id=source.id,
            sha256=source.sha256, filename="synthetic.xlsx", status="parsed")
        db.add(document); db.flush()
        job = IngestionJob(organization_id=org.id, document_id=document.id, status="completed", manifest={})
        db.add(job); db.flush()
        record = ExtractedSourceRecord(job_id=job.id,
            locator={"sheet": 1, "sheet_name": "CLAIMS", "row": 2}, values={"patient_name": "SYN-PRIVATE"})
        batch = ClaimBatch(organization_id=org.id, ingestion_document_id=document.id,
            created_by=actor.id, source_sha256=source.sha256, record_count=1, imported_count=1)
        db.add_all([record, batch]); db.flush()
        claim = ClaimEntry(organization_id=org.id, batch_id=batch.id, extracted_record_id=record.id,
            source_locator=record.locator, source_values=record.values,
            claim_reference="SYN-CLAIM", beneficiary_token="SYN-NO-PATIENT", provider_code="SYN-P",
            service_code="SYN-S", service_date=date(2026, 1, 5), claimed_amount="100", currency="USD")
        db.add(claim); db.flush()
        references = [{"family": family, "id": str(uuid4()), "version": 1,
            "status": "reference_incomplete", "evidence_ids": [source.id],
            "gaps": ["source_missing"]} for family in sorted(REFERENCE_FAMILIES)]
        certificates = [{"family": reference["family"], "reference_id": reference["id"],
            "version": reference["version"], "lookup_status": reference["status"],
            "source_evidence": [{"source_id": source.id}], "gaps": reference["gaps"]}
            for reference in references]
        snapshot = AuditSnapshot(organization_id=org.id, claim_id=claim.id,
            policy_id="SYN-POLICY", policy_fingerprint="b" * 64, calculation={"status": "held"},
            findings={"audit_state": "UNRESOLVED_OR_MISSING_REFERENCE",
                "reference_certificates": certificates}, verification={}, created_by=actor.id)
        db.add(snapshot); db.flush()
        details = {"audit_snapshot_id": snapshot.id, "source_record_id": record.id,
            "document_id": document.id, "source_sha256": source.sha256,
            "policy_fingerprint": snapshot.policy_fingerprint,
            "audit_state": snapshot.findings["audit_state"],
            "references": references}
        db.commit()
        return org.id, actor.id, claim.id, details


def _write(db, org, actor, claim, details):
    return write_event(db, actor=db.get(User, actor), organization_id=org,
        action="claim_inputs_audited", resource_type="claim_entry", resource_id=claim,
        outcome="success", details=details)


def test_claim_event_commit_reopen_dedup_and_privacy(engine):
    org, actor, claim, details = _seed(engine)
    with Session(engine) as db:
        event_id = _write(db, org, actor, claim, {**details,
            "patient_name": "SYN-PRIVATE", "diagnosis": "SYN-PRIVATE", "source_values": {"phi": "SYN-PRIVATE"}}).id
        db.commit()
    with Session(engine) as db:
        row = db.get(AuditLog, event_id)
        assert row.resource_id == claim
        assert row.details["audit_snapshot_id"] == details["audit_snapshot_id"]
        assert row.details["source_record_id"] == details["source_record_id"]
        assert len(row.details["references"]) == 6
        assert {reference["version"] for reference in row.details["references"]} == {1}
        assert "SYN-PRIVATE" not in json.dumps(row.details)
        assert _write(db, org, actor, claim, details).id == event_id
        db.commit()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_claim_event_rollback_and_retry(engine):
    org, actor, claim, details = _seed(engine)
    with Session(engine) as db:
        event_id = _write(db, org, actor, claim, details).id
        db.rollback()
    with Session(engine) as db:
        assert db.get(AuditLog, event_id) is None
        assert _write(db, org, actor, claim, details).id == event_id
        db.commit()
    with Session(engine) as db:
        assert db.get(AuditLog, event_id) is not None


def test_claim_event_concurrent_retries_store_one_row(engine):
    org, actor, claim, details = _seed(engine)
    def attempt(_):
        with Session(engine) as db:
            event_id = _write(db, org, actor, claim, details).id
            db.commit()
            return event_id
    with ThreadPoolExecutor(max_workers=6) as pool:
        ids = list(pool.map(attempt, range(12)))
    assert len(set(ids)) == 1
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_claim_event_conflicting_retry_fails_closed(engine):
    org, actor, claim, details = _seed(engine)
    with Session(engine) as db:
        _write(db, org, actor, claim, details)
        db.commit()
    changed = {**details, "references": [dict(reference) for reference in details["references"]]}
    changed["references"][0]["version"] = 2
    with Session(engine) as db:
        with pytest.raises(ValueError, match="reference correlation mismatch"):
            _write(db, org, actor, claim, changed)
        db.rollback()
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 1


def test_claim_event_cross_tenant_and_forged_source_rejected(engine):
    org, actor, claim, details = _seed(engine)
    with Session(engine) as db:
        foreign = Organization(name="SYN-FOREIGN")
        db.add(foreign); db.flush()
        outsider = User(organization_id=foreign.id, username="SYN-outsider", password_hash="unused")
        db.add(outsider); db.commit()
        with pytest.raises(ValueError, match="correlation mismatch"):
            _write(db, foreign.id, outsider.id, claim, details)
        with pytest.raises(ValueError, match="correlation mismatch"):
            _write(db, org, actor, claim, {**details, "source_sha256": "c" * 64})
        db.rollback()
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 0


def test_missing_reference_is_preserved_without_free_text():
    details = {key: str(uuid4()) for key in ("audit_snapshot_id", "source_record_id", "document_id")}
    details.update(source_sha256="a" * 64, policy_fingerprint="b" * 64,
        audit_state="AUDIT_NOT_POSSIBLE", references=[{"family": family, "id": None,
            "version": None, "status": "reference_missing", "evidence_ids": [],
            "gaps": ["reference_missing"]} for family in sorted(REFERENCE_FAMILIES)])
    safe = clean_claim_audit_details(details)
    assert all(reference["id"] is None for reference in safe["references"])
    details["references"][0]["gaps"] = ["Patient diagnosis"]
    with pytest.raises(ValueError, match="gap code"):
        clean_claim_audit_details(details)
