"""E1 real G2 -> approved CLAIMS-only G4 -> committed PG16 source proof."""
import hashlib
import io
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from openpyxl import Workbook
from alembic import command
from alembic.config import Config
from mcias.models import Organization, User, SourceFile, Role, Permission, UserRole, RolePermission, AuditLog
from mcias.models_ingestion import IngestionDocument, ExtractedSourceRecord
from mcias.models_claims import ClaimEntry
from mcias.ingestion.orchestrator import ingest
from mcias.storage import EncryptedStore
from mcias.claim_batches import stage, resume, preview, approve_source_scope, source_scope, BatchConflict


@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"), reason="PG16 required; executed by mandatory dedicated E1 workflow")
def test_e1_real_g2_to_g4_postgres_synthetic(tmp_path):
    url = os.environ["MCIAS_TEST_DATABASE_URL"]
    command.upgrade(Config("alembic.ini"), "head")
    book = Workbook()
    claims = book.active
    claims.title = "CLAIMS"
    claims.append(["claim_reference", "beneficiary_token", "provider_code",
                   "service_code", "service_date", "claimed_amount", "currency"])
    claims.append(["SYN-E1-C1", "SYN-E1-B1", "SYN-E1-P1", "SYN-E1-S1",
                   "2026-09-15", "120.00", "USD"])
    payment = book.create_sheet("PAYMENT")
    # Deliberately valid claim-shaped data: exclusion must use approved scope,
    # never accidental normalization failure of a PAYMENT row.
    payment.append(["claim_reference", "beneficiary_token", "provider_code",
                    "service_code", "service_date", "claimed_amount", "currency"])
    payment.append(["SYN-E1-PAY1", "SYN-E1-B1", "SYN-E1-P1", "SYN-E1-S1",
                    "2026-09-16", "90.00", "USD"])
    buf = io.BytesIO()
    book.save(buf)
    book.close()
    raw = buf.getvalue()
    digest = hashlib.sha256(raw).hexdigest()
    engine = create_engine(url)
    store = EncryptedStore(str(tmp_path), b"e" * 32)
    with Session(engine, expire_on_commit=False) as db:
        org = Organization(name="SYN-E1-ORG")
        actor = User(username="syn-e1-user-" + uuid4().hex, password_hash="fixture")
        db.add_all([org, actor])
        db.flush()
        actor.organization_id = org.id
        role = Role(code="syn-e1-import-" + uuid4().hex)
        permission = db.scalar(select(Permission).where(Permission.code == "claims.import"))
        if permission is None:
            permission = Permission(code="claims.import")
            db.add(permission)
        db.add(role)
        db.flush()
        db.add_all([UserRole(user_id=actor.id, role_id=role.id),
                    RolePermission(role_id=role.id, permission_id=permission.id)])
        db.commit()
        org_id, actor_id = org.id, actor.id
        result = ingest(db, store, org_id, actor_id, "synthetic-e1.xlsx", raw)
        assert result["status"] == "extracted", result
        assert result["sha256"] == digest
        doc_id = result["document_id"]
        document = db.get(IngestionDocument, doc_id)
        source = db.get(SourceFile, document.source_id)
        assert store.get(source.storage_key, source.sha256) == raw
        records = db.scalars(select(ExtractedSourceRecord).where(
            ExtractedSourceRecord.job_id == result["job_id"])).all()
        assert len(records) == 2
        assert {(r.locator["index"], r.locator["row"]) for r in records} == {(1, 2), (2, 2)}
        assert {r.locator["sheet_name"] for r in records} == {"CLAIMS", "PAYMENT"}
        with pytest.raises(BatchConflict, match="approved source scope"):
            stage(db, actor, doc_id)
        approval = approve_source_scope(db, actor, doc_id, {1: "CLAIMS", 2: "PAYMENT"})
        approval_id = approval.id
        assert approve_source_scope(db, actor, doc_id, {1: "CLAIMS", 2: "PAYMENT"}).id == approval_id
        assert "SYN-E1-B1" not in str(approval.details)
        scope = source_scope(db, actor, doc_id)
        assert (scope["source_records"], scope["eligible_records"], scope["excluded_records"]) == (2, 1, 1)
        batch = stage(db, actor, doc_id)
        assert stage(db, actor, doc_id).id == batch.id
        assert batch.record_count == 1
        assert len(preview(db, actor, batch.id)["rows"]) == 1
        outcome = resume(db, actor, batch.id)
        assert outcome["imported_count"] == 1, outcome
        assert outcome["status"] == "imported", outcome
        assert outcome["excluded_count"] == 1
        batch_id = batch.id
    with Session(engine) as independent:
        claims = independent.scalars(select(ClaimEntry).where(
            ClaimEntry.batch_id == batch_id)).all()
        assert len(claims) == 1
        assert claims[0].organization_id == org_id
        locator = claims[0].source_locator
        assert {k: locator[k] for k in ("kind", "index", "row", "column", "sheet_name")} == {
            "kind": "sheet", "index": 1, "row": 2, "column": None, "sheet_name": "CLAIMS"}
        assert locator["source_scope_approval_id"] == approval_id
        assert locator["source_sha256"] == digest
        assert locator["document_id"] == doc_id
        assert locator["sheet_type"] == "CLAIMS"
        assert locator["mapping_version"] == "g4-canonical-v1"
        assert claims[0].claim_reference == "SYN-E1-C1"
        assert claims[0].source_values["claimed_amount"] == "120.00"
        original = independent.get(ExtractedSourceRecord, claims[0].extracted_record_id)
        assert claims[0].source_values == original.values
        assert all(locator[k] == v for k, v in original.locator.items())
        assert independent.get(IngestionDocument, doc_id).sha256 == digest
        actor = independent.get(User, actor_id)
        assert resume(independent, actor, batch_id)["imported_count"] == 1
        assert independent.scalar(select(func.count()).select_from(ClaimEntry).where(
            ClaimEntry.batch_id == batch_id)) == 1
        assert independent.scalar(select(func.count()).select_from(AuditLog).where(
            AuditLog.action == "claim_source_scope_approved", AuditLog.resource_id == doc_id)) == 1
        other_org = Organization(name="SYN-E1-FOREIGN")
        other = User(username="syn-e1-other-" + uuid4().hex, password_hash="fixture")
        independent.add_all([other_org, other])
        independent.flush()
        other.organization_id = other_org.id
        independent.commit()
        for operation in (lambda: stage(independent, other, doc_id),
                          lambda: preview(independent, other, batch_id),
                          lambda: resume(independent, other, batch_id),
                          lambda: source_scope(independent, other, doc_id)):
            with pytest.raises(BatchConflict, match="not accessible"):
                operation()
    engine.dispose()
