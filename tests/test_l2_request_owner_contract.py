"""L2-SEC-001: request transaction owner contract, NOT the PR #25 integration test.

Uses the actual FastAPI get_db generator and original permission/tenant guards.
The audit sink is replaced by a recording spy ONLY to assert invocation order
and cardinality. Real writer persistence remains blocked until PR #25 exists.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User
from mcias.auth import require_permission
from mcias.tenant import require_organization
from mcias.denial_events import AuthorizationDenied
import mcias.app as application
import mcias.denial_events as denials


@pytest.mark.parametrize("guard", ["permission", "organization"])
def test_request_owner_rollback_before_one_audit_call(monkeypatch, tmp_path, guard):
    url = "sqlite:///" + str(tmp_path / "l2-request.sqlite")
    eng = create_engine(url)
    Base.metadata.create_all(eng)
    with Session(eng) as db:
        org = Organization(name="L2-SYNTHETIC-owner")
        db.add(org)
        db.flush()
        actor = User(username="l2-owner-" + guard, password_hash="synthetic", organization_id=org.id)
        db.add(actor)
        db.commit()
        org_id, actor_id = org.id, actor.id
    eng.dispose()

    class Settings:
        database_url = url

    calls = []

    def audit_spy(bind, denial):
        with Session(bind) as independent:
            observed = independent.get(Organization, org_id).name
        calls.append((denial.audit_action, observed, denial.audit_actor_id))

    monkeypatch.setattr(denials, "record_denial_after_rollback", audit_spy)
    iterator = application.get_db(Settings())
    db = next(iterator)
    org = db.get(Organization, org_id)
    actor = db.get(User, actor_id)
    org.name = "L2-UNAUTHORIZED"
    try:
        if guard == "permission":
            require_permission(db, actor, "l2.never.granted")
        else:
            require_organization(db, actor, org_id, "l2.never.granted")
    except AuthorizationDenied as exc:
        with pytest.raises(AuthorizationDenied):
            iterator.throw(exc)
    else:
        pytest.fail("guard must deny")
    with Session(create_engine(url)) as check:
        assert check.get(Organization, org_id).name == "L2-SYNTHETIC-owner"
    assert calls == [("permission_denied" if guard == "permission" else "tenant_access_denied",
                      "L2-SYNTHETIC-owner", actor_id)]
