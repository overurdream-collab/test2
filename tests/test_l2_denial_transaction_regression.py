"""L2-SEC-001: original guards must not commit unapproved business writes.

PostgreSQL proof requires an isolated provisioned database. No migrations or
schema changes are performed here; test uses the existing migrated schema.
"""
import os
from urllib.parse import urlsplit
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from mcias.auth import require_permission
from mcias.tenant import require_organization
from mcias.models import Organization, User, AuditLog


@pytest.fixture
def engine():
    url = os.environ.get("MCIAS_L2_ISOLATED_DATABASE_URL")
    if not url:
        pytest.skip("BLOCKED: isolated PostgreSQL not provisioned")
    p = urlsplit(url)
    if p.scheme not in ("postgresql", "postgresql+psycopg", "postgresql+psycopg2"):
        pytest.fail("PostgreSQL only")
    if p.hostname not in ("localhost", "127.0.0.1", "::1") or not (p.path or "").endswith("_l2_e2e"):
        pytest.fail("Refusing nonlocal or non-isolated database")
    if os.environ.get("MCIAS_L2_ALLOW_ISOLATED_TESTS") != "YES":
        pytest.fail("Explicit isolated DB confirmation required")
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.mark.parametrize("guard", ["permission", "organization"])
def test_denied_guard_never_commits_pending_work(engine, guard):
    # Uses a pre-existing synthetic fixture, supplied by a separate L1 setup.
    actor_id = os.environ.get("MCIAS_L2_SYNTHETIC_ACTOR_ID")
    org_id = os.environ.get("MCIAS_L2_SYNTHETIC_ORGANIZATION_ID")
    if not actor_id or not org_id:
        pytest.skip("BLOCKED: pre-provisioned synthetic fixture missing")
    with Session(engine) as db:
        actor = db.get(User, actor_id)
        assert actor and actor.organization_id == org_id
        # An uncommitted business update whose persistence can be verified
        # through a new session, without inserting/deleting records.
        original = db.get(Organization, org_id)
        assert original
        before = original.name
        marker = "L2-PENDING-WRITE-SHOULD-NOT-COMMIT"
        original.name = marker
        with pytest.raises(HTTPException) as e:
            if guard == "permission":
                require_permission(db, actor, "l2.never.granted")
            else:
                require_organization(db, actor, org_id, "l2.never.granted")
        assert e.value.status_code == 403
        db.rollback()
    with Session(engine) as check:
        assert check.get(Organization, org_id).name == before, "FAIL: denied request committed business write"
        # Auditing via the app's transaction owner / shared writer is verified
        # separately once the PR #25 dependency is integrated.
