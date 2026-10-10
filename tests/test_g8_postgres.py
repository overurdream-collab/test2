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
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()=="0015_g8_intelligence"
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
