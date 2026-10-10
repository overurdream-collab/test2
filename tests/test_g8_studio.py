"""G8 Analysis Studio lifecycle T15/T19: default deny, testing and separate approval."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from fastapi import HTTPException
import pytest

from mcias.models import Base, Organization, User
from mcias.models_ingestion import IngestionDocument  # noqa: F401
from mcias.models_claims import ClaimEntry  # noqa: F401
from mcias.models_audit import AuditSnapshot  # noqa: F401
from mcias.models_governance_g6 import GovernanceCase  # noqa: F401
from mcias.models_reporting_g7 import ReportSnapshot  # noqa: F401
from mcias.models_g8 import AnalysisTaskVersion, AnalysisTaskEvent, AnalysisRun
from mcias.intelligence_g8 import SOURCE, IntelligenceBlocked
from mcias import intelligence_service_g8 as svc
from mcias import intelligence_g8_api as api

def cfg(threshold="65"):
    return {"source":SOURCE,"indicator":"hold_rate","dimension":"provider",
            "threshold_percent":threshold,"min_group_size":5}

@pytest.fixture
def database():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        org=Organization(name="synthetic-org-g8")
        creator=User(username="g8-synthetic-creator",password_hash="test")
        tester=User(username="g8-synthetic-tester",password_hash="test")
        reviewer=User(username="g8-synthetic-reviewer",password_hash="test")
        foreign=Organization(name="synthetic-g8-other")
        intruder=User(username="g8-synthetic-foreign",password_hash="test")
        db.add_all([org,foreign,creator,tester,reviewer,intruder])
        db.flush()
        for user in (creator,tester,reviewer):
            user.organization_id=org.id
        intruder.organization_id=foreign.id
        db.commit()
        yield db,creator,tester,reviewer,intruder
    engine.dispose()

def test_t19_draft_never_activates_without_internal_test_and_independent_review(database,monkeypatch):
    db,creator,tester,reviewer,_=database
    monkeypatch.setattr(svc,"has_permission",lambda *_:True)
    task=svc.create_task(db,creator,"provider_hold_rate",cfg())
    assert task.version==1 and svc.task_status(db,task)=="draft"
    with pytest.raises(IntelligenceBlocked,match="T19"):
        svc.activate_task(db,reviewer,task.id)
    evidence=svc.test_task(db,tester,task.id)
    assert evidence.kind=="tested" and evidence.evidence["test"]["verification"]=="deterministic_controls_passed"
    assert evidence.evidence["test_digest"]
    with pytest.raises(IntelligenceBlocked,match="independent"):
        svc.activate_task(db,tester,task.id)
    with pytest.raises(IntelligenceBlocked,match="T19"):
        svc.test_task(db,tester,task.id)
    event=svc.activate_task(db,reviewer,task.id)
    assert event.kind=="activated" and event.version==2
    assert event.actor_id != task.created_by
    assert event.actor_id != evidence.actor_id
    assert svc.task_status(db,task)=="activated"
    with pytest.raises(IntelligenceBlocked,match="T19"):
        svc.activate_task(db,reviewer,task.id)
    retired=svc.deactivate_task(db,reviewer,task.id)
    assert retired.kind=="deactivated" and retired.version==3
    assert svc.task_status(db,task)=="deactivated"

def test_t19_tampered_evidence_never_enables_run(database,monkeypatch):
    db,creator,tester,reviewer,_=database
    monkeypatch.setattr(svc,"has_permission",lambda *_:True)
    task=svc.create_task(db,creator,"provider_signal",cfg())
    evidence=svc.test_task(db,tester,task.id)
    # Simulate a corrupt historical JSON payload outside ORM; activation rechecks digest.
    evidence.evidence={**evidence.evidence,"test_digest":"0"*64}
    with pytest.raises(IntelligenceBlocked,match="evidence mismatch"):
        svc.activate_task(db,reviewer,task.id)
    db.rollback()

def test_t19_new_version_requires_retest_and_prior_version_deactivation(database,monkeypatch):
    db,creator,tester,reviewer,_=database
    monkeypatch.setattr(svc,"has_permission",lambda *_:True)
    old=svc.create_task(db,creator,"cost_signal",cfg())
    svc.test_task(db,tester,old.id)
    svc.activate_task(db,reviewer,old.id)
    newer=svc.create_task(db,creator,"cost_signal",cfg("70"))
    assert newer.version==2 and newer.fingerprint!=old.fingerprint
    assert svc.task_status(db,newer)=="draft"
    svc.test_task(db,tester,newer.id)
    with pytest.raises(IntelligenceBlocked,match="another version"):
        svc.activate_task(db,reviewer,newer.id)
    svc.deactivate_task(db,reviewer,old.id)
    assert svc.activate_task(db,reviewer,newer.id).kind=="activated"
    assert svc.task_status(db,old)=="deactivated"
    assert svc.task_status(db,newer)=="activated"

def test_t15_foreign_tenant_and_role_denied(database,monkeypatch):
    db,creator,tester,reviewer,intruder=database
    monkeypatch.setattr(svc,"has_permission",lambda *_:True)
    task=svc.create_task(db,creator,"tenant_guard",cfg())
    with pytest.raises(IntelligenceBlocked,match="not accessible"):
        svc.test_task(db,intruder,task.id)
    monkeypatch.setattr(svc,"has_permission",lambda *_:False)
    with pytest.raises(IntelligenceBlocked,match="permission denied"):
        svc.test_task(db,tester,task.id)
    with pytest.raises(IntelligenceBlocked,match="permission denied"):
        svc.create_run(db,creator,"summary",["some-report"],{})
    with pytest.raises(IntelligenceBlocked,match="permission denied"):
        svc.activate_task(db,reviewer,task.id)

def test_t19_inactive_task_cannot_run_financial_or_signal_actions(database,monkeypatch):
    db,creator,tester,reviewer,_=database
    monkeypatch.setattr(svc,"has_permission",lambda *_:True)
    task=svc.create_task(db,creator,"inactive_probe",cfg())
    with pytest.raises(IntelligenceBlocked,match="T19"):
        svc.create_run(db,creator,"signals",["report-1"],{},task.id)
    assert db.scalars(select(AnalysisRun)).all()==[]
    svc.test_task(db,tester,task.id)
    with pytest.raises(IntelligenceBlocked,match="T19"):
        svc.create_run(db,creator,"signals",["report-1"],{},task.id)

def test_api_T15_capabilities_is_denied_without_server_permission(monkeypatch):
    actor=SimpleNamespace(id="actor",organization_id="org1",active=True)
    monkeypatch.setattr(api,"resolve_user",lambda *_:(actor,None))
    def denied(*_args):
        raise HTTPException(status_code=403,detail="forbidden")
    monkeypatch.setattr(api,"require_organization",denied)
    with pytest.raises(HTTPException) as exc:
        api.capabilities(db=MagicMock())
    assert exc.value.status_code==403

def test_api_T19_client_cannot_supply_activation_flags(monkeypatch):
    assert "approved" not in api.NewTask.model_fields
    assert "tested" not in api.NewTask.model_fields
    assert "signature_verified" not in api.NewTask.model_fields
    assert "sql" not in api.NewTask.model_fields
    assert "query" not in api.RunRequest.model_fields
    assert set(api.RunRequest.model_fields)=={"kind","report_ids","parameters","task_id"}
