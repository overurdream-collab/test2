"""Temporary composition acceptance: REAL FastAPI dependency, guards, PR25 writer and PG16.
PR25 writer is injected into disposable CI checkout, NEVER committed to PR27.
"""
import os
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import Depends, FastAPI, Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from mcias.app import get_db, get_settings
from mcias.auth import resolve_user
from mcias.tenant import require_organization, require_sensitive_field
from mcias.models import Organization, User, SessionToken, AuditLog

DB = os.environ["MCIAS_L2_ISOLATED_DATABASE_URL"]
ACTOR = os.environ["MCIAS_L2_SYNTHETIC_ACTOR_ID"]
ORG = os.environ["MCIAS_L2_SYNTHETIC_ORGANIZATION_ID"]


def test_http_rejected_mutation_rolls_back_and_audits_exactly_once():
    assert os.environ["MCIAS_L2_ALLOW_ISOLATED_TESTS"] == "YES"
    assert DB.endswith("/mcias_l2_e2e") and ("@127.0.0.1:" in DB or "@localhost:" in DB)
    engine = create_engine(DB)
    with Session(engine) as setup:
        actor = setup.get(User, ACTOR)
        assert actor and actor.active and actor.organization_id == ORG
        org = setup.get(Organization, ORG)
        assert org and org.name.startswith("L2-SYNTHETIC-")
        before = org.name
        # Token is synthetic and scoped to this disposable DB.
        token = "l2-sec001-isolated-test-token"
        setup.add(SessionToken(user_id=ACTOR, token_hash=sha256(token.encode()).hexdigest(),
                               expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)))
        setup.commit()

    app = FastAPI()
    class Settings:
        database_url = DB
    app.dependency_overrides[get_settings] = lambda: Settings()

    @app.post("/l2/denied")
    def denied(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
        user, _ = resolve_user(db, authorization)
        org = db.get(Organization, ORG)
        org.name = "L2-UNAUTHORIZED-MUTATION"
        require_organization(db, user, ORG, "l2.sec001.nonexistent.write")
        return {"unsafe": True}

    @app.post("/l2/medical-denial")
    def medical_denial(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
        user, _ = resolve_user(db, authorization)
        db.get(Organization, ORG).name = "L2-UNAPPROVED"
        require_sensitive_field(db, user, ORG, "diagnosis")
        return {"allowed": True}

    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.post("/l2/denied", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 403, response.text

    with Session(engine) as reader:
        assert reader.get(Organization, ORG).name == before
        rows = reader.scalars(select(AuditLog).where(
            AuditLog.actor_id == ACTOR,
            AuditLog.action == "tenant_access_denied")).all()
        assert len(rows) == 1, "must persist exactly one event"
        event = rows[0]
        assert event.resource_type == "organization"
        assert event.resource_id == ORG
        assert event.details.get("organization_id") == ORG
        assert event.details.get("outcome") == "denied"
        assert event.details.get("reason_code") == "tenant_or_permission_denied"
        assert "secret" not in str(event.details).lower()
        assert "patient" not in str(event.details).lower()
        assert "diagnosis" not in str(event.details).lower()
    # Cross-tenant validation against the real writer: forged organization never logs.
    from mcias.audit_writer import record_outcome_independent
    import pytest
    with Session(engine) as seed:
        foreign = Organization(name="L2-SYNTHETIC-FOREIGN")
        seed.add(foreign)
        seed.commit()
        foreign_id = foreign.id
    with pytest.raises(ValueError, match="mismatch"):
        record_outcome_independent(
            engine, actor_id=ACTOR, organization_id=foreign_id,
            action="tenant_access_denied", resource_type="organization",
            resource_id=foreign_id, outcome="denied",
            details={"reason_code": "tenant_or_permission_denied",
                     "medical_secret": "NEVER_LOG_THIS_SECRET"})
    with Session(engine) as independent:
        assert independent.scalar(select(AuditLog).where(
            AuditLog.actor_id == ACTOR,
            AuditLog.resource_id == foreign_id)) is None
        assert independent.scalar(select(AuditLog).where(
            AuditLog.actor_id == ACTOR,
            AuditLog.action == "tenant_access_denied")).id == event.id
    with TestClient(app, raise_server_exceptions=True) as client:
        second = client.post("/l2/medical-denial", headers={"Authorization": "Bearer " + token})
    assert second.status_code == 403
    with Session(engine) as verify:
        assert verify.get(Organization, ORG).name == before
        events = verify.scalars(select(AuditLog).where(
            AuditLog.actor_id == ACTOR, AuditLog.action == "tenant_access_denied")).all()
        assert len(events) == 2
        assert len({e.id for e in events}) == 2
        assert all(e.details.get("organization_id") == ORG for e in events)
    engine.dispose()
