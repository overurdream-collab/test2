"""Synthetic regression: date-scoped clauses, immutable revisions and four-way audit triage."""
from datetime import date, timedelta, datetime, timezone
from types import SimpleNamespace
from hashlib import sha256
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from mcias.app import app, get_db
from mcias.models import (Base, Organization, User, SourceFile, WrittenAuthorization,
                          SessionToken, Permission, Role, UserRole, RolePermission)
from mcias.models_input_clauses import InputClause, InputClauseEvent
from mcias.input_clause_service import (InputClauseError, create_draft, authorize_draft,
                                        list_points, at_date)
from mcias.audit_triage_api import classify_snapshot, GROUPS

@pytest.fixture
def local_db(monkeypatch):
    monkeypatch.setenv("MCIAS_ENVIRONMENT", "development")
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Organization(id="oa",name="Synthetic A"),Organization(id="ob",name="Synthetic B")])
        db.add_all([User(id="author",organization_id="oa",username="author-a",password_hash="synthetic"),
            User(id="reviewer",organization_id="oa",username="reviewer-a",password_hash="synthetic"),
            User(id="signer",organization_id="oa",username="signer-a",password_hash="synthetic"),
            User(id="foreign",organization_id="ob",username="foreign-b",password_hash="synthetic")])
        db.flush()
        db.add(SourceFile(id="source-a",sha256="a"*64,original_filename="synthetic.pdf",storage_key="fixture-a"))
        db.flush()
        db.add(WrittenAuthorization(id="approval-a",organization_id="oa",source_id="source-a",
             approved_by="signer",approved_at=datetime.now(timezone.utc)))
        db.add(Role(id="reference-role",code="synthetic_reference_role"))
        for code in ["reference.read","reference.write","reference.approve","reports.read","claims.read"]:
            db.add(Permission(id=code,code=code))
        db.flush()
        for code in ["reference.read","reference.write","reference.approve","reports.read","claims.read"]:
            db.add(RolePermission(role_id="reference-role",permission_id=code))
        for user in ["author","reviewer"]:
            db.add(UserRole(user_id=user,role_id="reference-role"))
        db.add(SessionToken(user_id="author",token_hash=sha256(b"synthetic-token").hexdigest(),
                            expires_at=datetime.now(timezone.utc)+timedelta(minutes=20)))
        db.commit()
    yield engine
    engine.dispose()

def make(db,actor,provider="hospital-a",amount="5000",start=None,replaces=None):
    return create_draft(db,actor,section="tariffs",logical_key="S01",provider_code=provider,
        insurer_code="insurer-a",clause_text="Synthetic consultation agreed tariff",
        structured_value={"service_code":"S01","amount":amount,"currency":"YER"},
        effective_from=start or date.today()-timedelta(days=60),replaces_id=replaces)

def resolve(db,actor,provider,on):
    return at_date(db,actor,section="tariffs",logical_key="S01",
                   provider_code=provider,insurer_code="insurer-a",on=on)

def test_provider_specific_prices_and_version_boundaries(local_db):
    with Session(local_db) as db:
        author,reviewer=db.get(User,"author"),db.get(User,"reviewer")
        first=make(db,author)
        second=make(db,author,provider="hospital-b",amount="7000")
        authorize_draft(db,reviewer,first.id,"approval-a")
        authorize_draft(db,reviewer,second.id,"approval-a")
        future=date.today()+timedelta(days=10)
        newer=make(db,author,amount="5500",start=future,replaces=first.id)
        authorize_draft(db,reviewer,newer.id,"approval-a")
        assert resolve(db,author,"hospital-a",future-timedelta(days=1))["id"]==first.id
        assert resolve(db,author,"hospital-a",future)["id"]==newer.id
        assert resolve(db,author,"hospital-b",future)["id"]==second.id
        assert list_points(db,author,"tariffs")[0]["section"]=="tariffs"
        assert db.scalars(select(InputClauseEvent).where(InputClauseEvent.clause_id==first.id)).all()
        with pytest.raises(ValueError,match="append-only"):
            db.delete(first);db.flush()
        db.rollback()
        assert db.get(InputClause,first.id) is not None

def test_refusal_of_self_approval_overlap_wrong_scope_and_retroactivity(local_db):
    with Session(local_db) as db:
        author,reviewer=db.get(User,"author"),db.get(User,"reviewer")
        first=make(db,author)
        with pytest.raises(InputClauseError,match="may not activate"):
            authorize_draft(db,author,first.id,"approval-a")
        authorize_draft(db,reviewer,first.id,"approval-a")
        duplicate=make(db,author)
        with pytest.raises(InputClauseError,match="overlapping"):
            authorize_draft(db,reviewer,duplicate.id,"approval-a")
        assert resolve(db,db.get(User,"foreign"),"hospital-a",date.today()) is None
        with pytest.raises(InputClauseError,match="scope"):
            make(db,author,provider="hospital-b",replaces=first.id)
        with pytest.raises(InputClauseError,match="retroactive"):
            make(db,author,start=date.today()-timedelta(days=1),replaces=first.id)
        with pytest.raises(InputClauseError,match="provider-specific"):
            make(db,author,provider="")
        with pytest.raises(InputClauseError,match="precision"):
            make(db,author,provider="hospital-x",amount="13.99999")

def test_api_requires_identity_and_tracks_draft(local_db):
    def dependency():
        with Session(local_db) as db: yield db
    app.dependency_overrides[get_db]=dependency
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/input-clauses/sections").status_code==401
            h={"Authorization":"Bearer synthetic-token"}
            assert "tariffs" in client.get("/api/v1/input-clauses/sections",headers=h).json()["sections"]
            r=client.post("/api/v1/input-clauses/points",headers=h,json={
                "section":"contracts","logical_key":"TERM","clause_text":"Term is one year",
                "structured_value":{"text":"one year"},"effective_from":date.today().isoformat()})
            assert r.status_code==201,r.text
            point=r.json()["id"]
            assert client.get("/api/v1/input-clauses/points/"+point,headers=h).json()["status"]=="draft"
            denied=client.post("/api/v1/input-clauses/points/"+point+"/activate",
                               headers=h,json={"authorization_id":"approval-a"})
            assert denied.status_code==409
    finally:
        app.dependency_overrides.pop(get_db,None)

def test_four_way_classifier_respects_independent_evidence():
    agents=("eligibility","contract","tariff","exclusion","caps","cost_sharing","duplicates","evidence")
    baseline=[{"agent":n,"status":"pass"} for n in agents]
    def snap(checks,verification="held",calculation="held"):
        return SimpleNamespace(findings={"agents":checks},verification={"status":verification},
                               calculation={"status":calculation})
    assert classify_snapshot(None)[0]=="HUMAN_REVIEW"
    assert classify_snapshot(snap(baseline,"verified","calculated"))[0]=="ACCEPTED_RULES"
    evidence=[dict(x) for x in baseline];evidence[-1]["status"]="hold"
    assert classify_snapshot(snap(evidence))[0]=="MISSING_ATTACHMENTS"
    unclear=[dict(x) for x in baseline];unclear[0]["status"]="hold"
    assert classify_snapshot(snap(unclear))[0]=="HUMAN_REVIEW"
    bad=[dict(x) for x in baseline];bad[0].update(status="fail_confirmed",
        independently_verified=True,approved_rule_version_id="approved-rule",evidence_ref="proof")
    assert classify_snapshot(snap(bad))[0]=="REJECTED_RULE_CERTAIN"
    bad[0].pop("evidence_ref")
    assert classify_snapshot(snap(bad))[0]=="HUMAN_REVIEW"
    assert len(GROUPS)==4
