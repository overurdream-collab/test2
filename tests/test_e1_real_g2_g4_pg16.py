"""E1 real G2 ingestion -> G4 batch PG16 diagnostic, synthetic only.

The current G4 contract has no trusted CLAIMS-only sheet gate. This test
documents actual behaviour and cannot be counted as accepted E1.
"""
import hashlib
import io
import os
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from openpyxl import Workbook
from alembic import command
from alembic.config import Config
from mcias.models import Organization, User, SourceFile
from mcias.models_ingestion import IngestionDocument, ExtractedSourceRecord
from mcias.models_claims import ClaimEntry
from mcias.ingestion.orchestrator import ingest
from mcias.storage import EncryptedStore
from mcias.claim_batches import stage, resume


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
    payment.append(["payment_reference", "claim_reference", "payment_date", "amount", "currency"])
    payment.append(["SYN-E1-PAY1", "SYN-E1-C1", "2026-09-16", "90.00", "USD"])
    buf = io.BytesIO()
    book.save(buf)
    book.close()
    raw = buf.getvalue()
    digest = hashlib.sha256(raw).hexdigest()
    engine = create_engine(url)
    store = EncryptedStore(str(tmp_path), b"e" * 32)
    with Session(engine, expire_on_commit=False) as db:
        org = Organization(name="SYN-E1-ORG")
        actor = User(username="syn-e1-user", password_hash="fixture")
        db.add_all([org, actor])
        db.flush()
        actor.organization_id = org.id
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
        batch = stage(db, actor, doc_id)
        outcome = resume(db, actor, batch.id)
        assert outcome["imported_count"] == 1, outcome
        assert outcome["status"] == "review_required", outcome
        batch_id = batch.id
    with Session(engine) as independent:
        claims = independent.scalars(select(ClaimEntry).where(
            ClaimEntry.batch_id == batch_id)).all()
        assert len(claims) == 1
        assert claims[0].organization_id == org_id
        assert claims[0].source_locator == {"kind": "sheet", "index": 1, "row": 2}
        assert independent.get(IngestionDocument, doc_id).sha256 == digest
    engine.dispose()
