from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, AuditLog
from mcias.models_ingestion import IngestionJob, QuarantineItem, IngestionDocument, ExtractedSourceRecord
from mcias.storage import EncryptedStore
from mcias.ingestion.orchestrator import ingest
from mcias.ingestion.reprocessing import retry
from mcias.ingestion.review import decide, ReviewDenied
import pytest

def test_reprocess_preserves_history_and_audits_review(tmp_path):
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    store=EncryptedStore(str(tmp_path),b"k"*32)
    with Session(engine) as db:
        org=Organization(name="synthetic")
        actor=User(username="reviewer",password_hash="fixture")
        db.add_all([org,actor]);db.flush()
        actor.organization_id=org.id
        db.commit()
        first=ingest(db,store,org.id,actor.id,"broken.xlsx",b"broken")
        item=db.query(QuarantineItem).one()
        with pytest.raises(ReviewDenied):
            decide(db,actor,first["job_id"],item.id,"acknowledge","short")
        decision=decide(db,actor,first["job_id"],item.id,"request_reupload","Unreadable workbook; please resubmit original")
        assert decision["decision"]=="request_reupload"
        with pytest.raises(ReviewDenied):
            decide(db,actor,first["job_id"],item.id,"reject","Duplicate review attempt is not permitted")
        second=retry(db,store,first["document_id"],actor)
        assert second["job_id"] != first["job_id"]
        assert db.query(IngestionJob).count()==2
        assert db.query(IngestionDocument).count()==1
        assert db.query(AuditLog).filter(AuditLog.action=="ingestion_reprocessed").count()==1
        assert db.query(AuditLog).filter(AuditLog.action=="ingestion_quarantine_reviewed").count()==1
    engine.dispose()

def test_cross_tenant_quarantine_review_denied(tmp_path):
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    store=EncryptedStore(str(tmp_path),b"k"*32)
    with Session(engine) as db:
        first_org=Organization(name="first")
        second_org=Organization(name="second")
        first=User(username="first",password_hash="fixture")
        second=User(username="second",password_hash="fixture")
        db.add_all([first_org,second_org,first,second]);db.flush()
        first.organization_id=first_org.id
        second.organization_id=second_org.id
        db.commit()
        record=ingest(db,store,first_org.id,first.id,"broken.xlsx",b"broken")
        item=db.query(QuarantineItem).one()
        with pytest.raises(ReviewDenied):
            decide(db,second,record["job_id"],item.id,"reject","This file cannot be read safely")
    engine.dispose()
