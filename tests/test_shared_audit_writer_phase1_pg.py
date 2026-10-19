"""Phase 1 writer contract on disposable, localhost PostgreSQL only.

Run with MCIAS_AUDIT_PHASE1_DATABASE_URL pointing to /mcias_audit_phase1
and MCIAS_AUDIT_PHASE1_ALLOW=YES. No migrations or production access.
"""
import os
from urllib.parse import urlsplit
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, AuditLog
from mcias.audit_writer import write_event, record_outcome_independent

@pytest.fixture
def engine():
    required = os.getenv("MCIAS_AUDIT_PHASE1_REQUIRED") == "YES"
    if not required and (os.getenv("MCIAS_AUDIT_PHASE1_ALLOW") != "YES" or not os.getenv("MCIAS_AUDIT_PHASE1_DATABASE_URL")):
        pytest.skip("Dedicated PostgreSQL fixture unavailable in general Unit runner")
    assert os.getenv("MCIAS_AUDIT_PHASE1_ALLOW") == "YES", "Explicit isolated test consent required"
    url = os.environ["MCIAS_AUDIT_PHASE1_DATABASE_URL"]
    p = urlsplit(url.replace("postgresql+psycopg://", "postgresql://", 1))
    assert p.scheme == "postgresql" and p.hostname in ("localhost", "127.0.0.1")
    assert p.path == "/mcias_audit_phase1"
    e = create_engine(url)
    # Test-owned minimal tables, never database migrations or existing tables.
    for table in (AuditLog.__table__, User.__table__, Organization.__table__):
        assert not __import__("sqlalchemy").inspect(e).has_table(table.name), "Disposable database must start empty"
    Base.metadata.create_all(e, tables=[Organization.__table__, User.__table__, AuditLog.__table__])
    try:
        yield e
    finally:
        Base.metadata.drop_all(e, tables=[AuditLog.__table__, User.__table__, Organization.__table__])
        e.dispose()

def _seed(engine):
    with Session(engine) as s:
        org = Organization(name="AW-PHASE1-SYNTHETIC")
        s.add(org); s.flush()
        actor = User(organization_id=org.id, username="aw-phase1-synthetic", password_hash="unused")
        s.add(actor); s.commit()
        return org.id, actor.id

def test_success_is_atomic_and_details_allowlisted(engine):
    org, uid = _seed(engine)
    with Session(engine) as s:
        actor = s.get(User, uid)
        evt = write_event(s, actor=actor, organization_id=org,
                          action="synthetic_success", resource_type="test", resource_id=None,
                          outcome="success", details={"version": 2, "medical_secret": "NEVER_STORE"})
        eid = evt.id
        s.rollback()
    with Session(engine) as s:
        assert s.get(AuditLog, eid) is None
        actor = s.get(User, uid)
        evt = write_event(s, actor=actor, organization_id=org,
                          action="synthetic_success", resource_type="test", resource_id=None,
                          outcome="success", details={"version": 2, "medical_secret": "NEVER_STORE"})
        eid = evt.id
        s.commit()
    with Session(engine) as s:
        row = s.get(AuditLog, eid)
        assert row.details == {"organization_id": org, "outcome": "success", "version": 2}

def test_independent_denial_survives_business_rollback(engine):
    org, uid = _seed(engine)
    with Session(engine) as s:
        row = s.get(Organization, org); row.name = "UNAUTHORIZED-CHANGE"
        s.flush()
        s.rollback()
    eid = record_outcome_independent(engine, actor_id=uid, organization_id=org,
                action="synthetic_denied", resource_type="test", resource_id=None,
                outcome="denied", details={"reason_code": "permission_denied"})
    with Session(engine) as s:
        assert s.get(Organization, org).name == "AW-PHASE1-SYNTHETIC"
        assert s.get(AuditLog, eid).details["outcome"] == "denied"

def test_wrong_tenant_inactive_and_unknown_actor_rejected(engine):
    org, uid = _seed(engine)
    with Session(engine) as s:
        foreign = Organization(name="AW-PHASE1-FOREIGN")
        s.add(foreign); s.commit(); foreign_id = foreign.id
    for actor_id, target in [(uid, foreign_id), ("00000000-0000-0000-0000-000000000000", org)]:
        with pytest.raises(ValueError):
            record_outcome_independent(engine, actor_id=actor_id, organization_id=target,
                action="synthetic_denied", resource_type="test", resource_id=None, outcome="denied")
    with Session(engine) as s:
        actor = s.get(User, uid); actor.active = False; s.commit()
    with pytest.raises(ValueError):
        record_outcome_independent(engine, actor_id=uid, organization_id=org,
            action="synthetic_denied", resource_type="test", resource_id=None, outcome="denied")
    with Session(engine) as s:
        assert s.scalars(select(AuditLog)).all() == []

def test_invalid_outcome_and_fields_fail_closed(engine):
    org, uid = _seed(engine)
    with Session(engine) as s:
        actor = s.get(User, uid)
        with pytest.raises(ValueError):
            write_event(s, actor=actor, organization_id=org, action="test",
                resource_type="test", resource_id=None, outcome="invalid")
        with pytest.raises(ValueError):
            write_event(s, actor=actor, organization_id=org, action="", 
                resource_type="test", resource_id=None, outcome="success")
        s.rollback()
