"""G7 T13/T20 real PostgreSQL persistence, idempotency and immutable historical versions.

All test claims and identifiers are synthetic. No approved institutional policy is implied.
"""
import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from mcias.audit_engine import AuditPolicy, evaluate
from mcias.models import Organization, User, SourceFile
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord
from mcias.models_claims import ClaimBatch, ClaimEntry
from mcias.models_audit import AuditSnapshot
from mcias.models_governance_g6 import GovernanceCase, GovernanceEvent
from mcias.models_reporting_g7 import ReportSnapshot
from mcias.reporting_g7 import create_snapshot, verify_snapshot, ReportBlocked

@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"), reason="PostgreSQL integration required")
def test_g7_postgres_real_freeze_idempotence_versioning_and_tenant_denial():
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(os.environ["MCIAS_TEST_DATABASE_URL"])
    unique = uuid4().hex[:14]
    with Session(engine, expire_on_commit=False) as db:
        org = Organization(name="G7 Synthetic " + unique)
        proposer = User(username="g7-propose-" + unique, password_hash="synthetic")
        approver = User(username="g7-approve-" + unique, password_hash="synthetic")
        db.add_all([org, proposer, approver]);db.flush()
        proposer.organization_id = approver.organization_id = org.id
        source = SourceFile(sha256="a" * 64, original_filename="synthetic.xlsx",
                            storage_key="g7-test-" + unique)
        db.add(source);db.flush()
        doc = IngestionDocument(organization_id=org.id, source_id=source.id,
                                sha256="a" * 64, filename="synthetic.xlsx", status="extracted")
        db.add(doc);db.flush()
        job = IngestionJob(organization_id=org.id, document_id=doc.id,
                           status="extracted", manifest={"complete":True})
        db.add(job);db.flush()
        raw_values = {"claim_reference":"SYN-G7", "claimed_amount":"200.00",
                      "beneficiary_token":"synthetic-only", "diagnosis":"synthetic-not-patient"}
        record = ExtractedSourceRecord(job_id=job.id, locator={"row":2},
                                       values=raw_values, confidence=100)
        db.add(record);db.flush()
        batch = ClaimBatch(organization_id=org.id, ingestion_document_id=doc.id,
                           created_by=proposer.id, status="imported",
                           source_sha256=doc.sha256, record_count=1, imported_count=1)
        db.add(batch);db.flush()
        claim = ClaimEntry(organization_id=org.id, batch_id=batch.id,
                           extracted_record_id=record.id, source_locator={"row":2},
                           source_values=raw_values, claim_reference="SYN-G7",
                           beneficiary_token="synthetic-only", provider_code="SYN",
                           service_code="SYN", service_date=date(2026,10,10),
                           claimed_amount=Decimal("200"), currency="YER")
        db.add(claim);db.flush()
        fixture_policy = AuditPolicy(policy_id="synthetic-g7", currency="YER",
            rounding="HALF_UP", precision=2,
            order=("exclusion","tariff","cap","copay"),
            exclusion=Decimal("10"), tariff=Decimal("100"),
            cap=Decimal("80"), copay_percent=Decimal("20"), approved=True)
        calculation = evaluate(Decimal("200"),"YER",fixture_policy,
            eligible=True,evidence_complete=True,source_id=record.id,
            contract_id="synthetic-contract",beneficiary_enrollment_id="synthetic-enrollment")
        snapshot = AuditSnapshot(organization_id=org.id, claim_id=claim.id,
                                 policy_id="synthetic-g7",policy_fingerprint="b"*64,
                                 calculation=calculation,findings={"agents":[]},
                                 verification={"status":"verified"},created_by=proposer.id)
        db.add(snapshot);db.flush()
        case=GovernanceCase(organization_id=org.id,claim_id=claim.id,
                            audit_snapshot_id=snapshot.id,opened_by=proposer.id)
        db.add(case);db.flush()
        db.add_all([
            GovernanceEvent(case_id=case.id,organization_id=org.id,version=1,
                kind="propose",actor_id=proposer.id,snapshot_id=snapshot.id,payload={}),
            GovernanceEvent(case_id=case.id,organization_id=org.id,version=2,
                kind="approve",actor_id=approver.id,snapshot_id=snapshot.id,payload={}),
        ])
        db.commit()
        first = create_snapshot(db, proposer, batch.id)
        assert first.version == 1
        assert first.summary["by_currency"]["YER"]["payable"] == "64.00"
        assert verify_snapshot(first)
        again = create_snapshot(db, proposer, batch.id)
        assert again.id == first.id
        assert again.version == 1
        first_hash, first_id = first.fingerprint, first.id
        db.add(GovernanceEvent(case_id=case.id, organization_id=org.id,version=3,
            kind="object",actor_id=proposer.id,snapshot_id=snapshot.id,
            evidence_document_id=doc.id,payload={"reason_code":"SYNTHETIC"}))
        db.commit()
        second = create_snapshot(db, proposer, batch.id)
        assert second.version == 2 and second.id != first_id
        assert second.summary["by_currency"]["YER"]["payable"] == "0"
        assert second.summary["by_currency"]["YER"]["held_count"] == 1
        old = db.get(ReportSnapshot, first_id)
        assert old.fingerprint == first_hash
        assert old.summary["by_currency"]["YER"]["payable"] == "64.00"
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE report_snapshots SET version = 99 WHERE id = :id"),
                       {"id": first_id})
            db.commit()
        db.rollback()
        other_org = Organization(name="G7 Other " + unique)
        outsider = User(username="g7-other-" + unique, password_hash="synthetic")
        db.add_all([other_org, outsider]);db.flush()
        outsider.organization_id = other_org.id
        db.commit()
        with pytest.raises(ReportBlocked, match="not accessible"):
            create_snapshot(db, outsider, batch.id)
    engine.dispose()
