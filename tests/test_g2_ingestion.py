import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, SourceFile
from mcias.models_ingestion import IngestionDocument, IngestionJob, QuarantineItem, ExtractedSourceRecord
from mcias.ingestion.orchestrator import ingest
from mcias.storage import EncryptedStore

def test_g2_t01_t02_original_preserved_duplicate_isolated(tmp_path):
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    store=EncryptedStore(str(tmp_path), b"k"*32)
    with Session(engine) as db:
        org=Organization(name="synthetic")
        actor=User(username="reader",password_hash="fixture")
        db.add_all([org,actor]);db.flush()
        actor.organization_id=org.id
        db.commit()
        malformed=b"broken-xlsx"
        first=ingest(db,store,org.id,actor.id,"broken.xlsx",malformed)
        assert first["status"]=="review_required"
        source=db.get(SourceFile,db.get(IngestionDocument,first["document_id"]).source_id)
        assert store.get(source.storage_key,source.sha256)==malformed
        assert db.query(QuarantineItem).count()==1
        again=ingest(db,store,org.id,actor.id,"broken.xlsx",malformed)
        assert again["status"]=="duplicate"
        assert again["document_id"]==first["document_id"]
        assert db.query(IngestionDocument).count()==1
        assert db.query(IngestionJob).count()==1
        good=ingest(db,store,org.id,actor.id,"claims.csv",b"claim,amount\nA,12\n")
        assert good["status"]=="extracted"
        assert good["manifest"]["complete"]
        record=db.query(ExtractedSourceRecord).one()
        assert record.locator["row"]==2
        assert record.values["amount"]=="12"
    engine.dispose()

def test_g2_tenant_specific_dedup(tmp_path):
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    store=EncryptedStore(str(tmp_path),b"k"*32)
    with Session(engine) as db:
        orgs=[Organization(name="org1"),Organization(name="org2")]
        users=[User(username="one",password_hash="fixture"),User(username="two",password_hash="fixture")]
        db.add_all(orgs+users);db.flush()
        for org,user in zip(orgs,users):
            user.organization_id=org.id
        db.commit()
        a=ingest(db,store,orgs[0].id,users[0].id,"same.csv",b"id\nA\n")
        b=ingest(db,store,orgs[1].id,users[1].id,"same.csv",b"id\nA\n")
        assert a["document_id"]!=b["document_id"]
        assert db.query(IngestionDocument).count()==2
    engine.dispose()
