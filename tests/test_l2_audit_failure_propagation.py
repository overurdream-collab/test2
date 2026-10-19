"""Fail-closed behavior when durable denial audit cannot be written.

This checks the real request owner. It does NOT claim to cover PostgreSQL
persistence, which is separately enforced by the mandatory L2 HTTP gate.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User
from mcias.tenant import require_organization
from mcias.denial_events import AuthorizationDenied
import mcias.denial_events as events
import mcias.app as app


def test_audit_writer_failure_does_not_commit_denied_business_mutation(tmp_path, monkeypatch):
    url = "sqlite:///" + str(tmp_path / "audit-failure.sqlite")
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tenant = Organization(name="L2-SYNTHETIC-FAILURE")
        db.add(tenant)
        db.flush()
        user = User(username="l2-failure-actor", password_hash="synthetic", organization_id=tenant.id)
        db.add(user)
        db.commit()
        tenant_id, user_id = tenant.id, user.id
    engine.dispose()

    def failed_write(bind, denial):
        raise RuntimeError("synthetic audit persistence failure")

    monkeypatch.setattr(events, "record_denial_after_rollback", failed_write)
    class Settings:
        database_url = url

    dependency = app.get_db(Settings())
    db = next(dependency)
    actor = db.get(User, user_id)
    db.get(Organization, tenant_id).name = "UNAUTHORIZED-CHANGE"
    with pytest.raises(AuthorizationDenied) as denial:
        require_organization(db, actor, tenant_id, "l2.not.granted")
    with pytest.raises(RuntimeError, match="synthetic audit persistence failure"):
        dependency.throw(denial.value)
    with Session(create_engine(url)) as independent:
        assert independent.get(Organization, tenant_id).name == "L2-SYNTHETIC-FAILURE"
