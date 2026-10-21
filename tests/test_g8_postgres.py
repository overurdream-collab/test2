"""G8 PostgreSQL T15/T19 actual tenant and append-only guards."""
import os
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
from mcias.models import Organization, User
from mcias.models_g8 import AnalysisTaskVersion, AnalysisTaskEvent, AnalysisRun
from mcias.intelligence_g8 import SOURCE, digest

import pytest

@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"),
                    reason="G8 PostgreSQL service required")
def test_g8_migration_task_lifecycle_and_db_mutation_guards():
    command.upgrade(Config("alembic.ini"), "head")
    engine=create_engine(os.environ["MCIAS_TEST_DATABASE_URL"])
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()=="0019_reference_dataset_v1"
        triggers={x[0] for x in conn.execute(text("""
            SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND tgname LIKE 'trg_g8_%'
        """))}
        assert {"trg_g8_task_immutable","trg_g8_event_immutable",
                "trg_g8_run_immutable"} <= triggers
    marker=uuid4().hex[:13]
    with Session(engine,expire_on_commit=False) as db:
        organization=Organization(name="synthetic G8 postgres "+marker)
        other=Organization(name="foreign G8 postgres "+marker)
        origin=User(username="g8pg_origin_"+marker,password_hash="synthetic")
        reviewer=User(username="g8pg_reviewer_"+marker,password_hash="synthetic")
        outsider=User(username="g8pg_outsider_"+marker,password_hash="synthetic")
        db.add_all([organization,other,origin,reviewer,outsider]);db.flush()
        origin.organization_id=reviewer.organization_id=organization.id
        outsider.organization_id=other.id
        config={"source":SOURCE,"indicator":"hold_rate","dimension":"provider",
                "threshold_percent":"60","min_group_size":5}
        task=AnalysisTaskVersion(organization_id=organization.id,code="hospital_signal",
             version=1,configuration=config,fingerprint=digest(config),created_by=origin.id)
        db.add(task);db.flush()
        event=AnalysisTaskEvent(organization_id=organization.id,task_id=task.id,
            version=1,kind="tested",actor_id=origin.id,
            evidence={"test_digest":"a"*64})
        db.add(event);db.commit()
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE g8_analysis_tasks SET version=2 WHERE id=:id"),{"id":task.id})
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(text("DELETE FROM g8_analysis_task_events WHERE id=:id"),{"id":event.id})
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError):
            db.add(AnalysisTaskEvent(organization_id=organization.id,
                task_id=task.id,version=2,kind="activated",
                actor_id=outsider.id,evidence={"test_digest":"a"*64}))
            db.commit()
        db.rollback()
        with pytest.raises(DBAPIError):
            db.add(AnalysisRun(organization_id=organization.id,
                kind="summary",sources=[{"report_id":"missing",
                  "fingerprint":"a"*64}],parameters={"dimension":"provider"},
                result={"review_only":True},fingerprint="b"*64,created_by=origin.id))
            db.commit()
        db.rollback()
        assert db.get(AnalysisTaskVersion,task.id).version==1
        assert db.get(AnalysisTaskEvent,event.id).kind=="tested"
    engine.dispose()

@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"),
                    reason="G8 PostgreSQL service required")
def test_g8_full_postgres_reports_to_analytics_to_review(monkeypatch):
    """End-to-end synthetic G4 -> frozen G7 -> G8 signal -> G8 review."""
    from datetime import date
    from decimal import Decimal
    from mcias.models import SourceFile
    from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord
    from mcias.models_claims import ClaimBatch, ClaimEntry
    from mcias.models_reporting_g7 import ReportSnapshot
    from mcias.reporting_g7 import fingerprint as report_fingerprint
    from mcias import intelligence_service_g8 as svc
    from mcias import intelligence_review_g8 as reviews

    command.upgrade(Config("alembic.ini"), "head")
    engine=create_engine(os.environ["MCIAS_TEST_DATABASE_URL"])
    marker=uuid4().hex[:12]
    with Session(engine,expire_on_commit=False) as db:
        org=Organization(name="G8 real PostgreSQL synthetic "+marker)
        owner=User(username="g8full_owner_"+marker,password_hash="synthetic")
        reviewer=User(username="g8full_reviewer_"+marker,password_hash="synthetic")
        db.add_all([org,owner,reviewer]);db.flush()
        owner.organization_id=reviewer.organization_id=org.id
        source=SourceFile(sha256="c"*64,original_filename="synthetic.csv",
                          storage_key="g8-full-"+marker)
        db.add(source);db.flush()
        doc=IngestionDocument(organization_id=org.id,source_id=source.id,
            sha256=source.sha256,filename="synthetic.csv",status="extracted")
        db.add(doc);db.flush()
        job=IngestionJob(organization_id=org.id,document_id=doc.id,
            status="extracted",manifest={"complete":True})
        db.add(job);db.flush()
        batch=ClaimBatch(organization_id=org.id,ingestion_document_id=doc.id,
            created_by=owner.id,status="imported",source_sha256=source.sha256,
            record_count=10,imported_count=10)
        db.add(batch);db.flush()
        frozen_rows=[]
        for index in range(10):
            values={"claim_reference":"SYN"+str(index),
                    "beneficiary_token":"private-"+str(index),
                    "amount":"100","diagnosis":"synthetic-only"}
            raw=ExtractedSourceRecord(job_id=job.id,
                locator={"kind":"row","index":index,"row":index+2},
                values=values,confidence=100)
            db.add(raw);db.flush()
            claim=ClaimEntry(organization_id=org.id,batch_id=batch.id,
                extracted_record_id=raw.id,source_locator=raw.locator,
                source_values=values,claim_reference=values["claim_reference"],
                beneficiary_token=values["beneficiary_token"],
                provider_code="P1" if index<5 else "P2",
                service_code="LAB" if index<5 else "PHARMACY",
                service_date=date(2026,1,index+1),claimed_amount=Decimal("100"),
                currency="YER")
            db.add(claim);db.flush()
            frozen_rows.append({"claim_id":claim.id,"source_record_id":raw.id,
                "claimed":"100","payable":"80","deduction":"20",
                "state":"approved","currency":"YER",
                "beneficiary_token":claim.beneficiary_token,
                "claim_reference":claim.claim_reference,
                "source_locator":raw.locator,"source_values":values})
        summary={"total_claims":10,"by_currency":{"YER":{
            "claimed":"1000","approved_claimed":"1000",
            "held_claimed":"0","payable":"800","deductions":"200",
            "approved_count":10,"held_count":0}}}
        dataset={"schema":1,"organization_id":org.id,
                 "batch_id":batch.id,"source_sha256":source.sha256,
                 "rows":frozen_rows}
        frozen=ReportSnapshot(organization_id=org.id,batch_id=batch.id,
            version=1,dataset=dataset,summary=summary,
            fingerprint=report_fingerprint(dataset,summary),created_by=owner.id)
        db.add(frozen);db.commit()
        monkeypatch.setattr(svc,"has_permission",lambda *_:True)
        analysis=svc.create_run(db,owner,"summary",[frozen.id],
             {"dimension":"provider","min_group_size":5})
        assert analysis.result["input_claim_count"]==10
        assert analysis.result["output"]["denominator_count"]==10
        assert sum(int(row["count"]) for row in analysis.result["output"]["groups"])==10
        assert all("private-" not in str(row)
                   for row in analysis.result["output"]["groups"])
        assert svc.verify_run(analysis)
        task=svc.create_task(db,owner,"g8full_provider_share",{
            "source":"g7_frozen_report_snapshots",
            "indicator":"provider_claimed_share","dimension":"provider",
            "threshold_percent":"40","min_group_size":5})
        tested=svc.test_task(db,owner,task.id)
        assert tested.kind=="tested"
        activated=svc.activate_task(db,reviewer,task.id)
        assert activated.kind=="activated"
        alerts=svc.create_run(db,owner,"signals",[frozen.id],{},task.id)
        assert len(alerts.result["output"]["findings"])==2
        assert alerts.result["output"]["no_automatic_deductions"]
        review=reviews.add_review(db,reviewer,alerts.id,0,
            "false_positive","CONTEXT_EXPLAINS")
        assert review.version==1
        quality=reviews.reviews_summary(db,reviewer,alerts.id)
        assert quality["reviewed_signals"]==1
        assert quality["signal_count"]==2
        assert quality["false_positive_rate_among_reviewed"]=="100"
        assert quality["unreviewed_signals"]==1
        persisted=db.get(AnalysisRun,alerts.id)
        assert svc.verify_run(persisted)
        assert db.get(ReportSnapshot,frozen.id).fingerprint==frozen.fingerprint
    engine.dispose()
