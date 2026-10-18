"""L2-SEC-001: original authorization guards must never commit pending business writes.

No migrations. Runs ONLY against a locally preprovisioned, disposable PostgreSQL
database and a disposable synthetic organization. The baseline FAIL is preserved
even though destructive test artifacts are restored in a separate transaction.
"""
import os
import uuid
from urllib.parse import urlsplit
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from fastapi import HTTPException
from mcias.auth import require_permission
from mcias.tenant import require_organization
from mcias.models import Organization, User, AuditLog

@pytest.fixture(scope="module")
def engine():
    url = os.environ.get("MCIAS_L2_ISOLATED_DATABASE_URL")
    if not url:
        pytest.fail("BLOCKED: isolated PostgreSQL not available; no PASS permitted")
    parsed = urlsplit(url)
    if parsed.scheme not in ("postgresql", "postgresql+psycopg", "postgresql+psycopg2"):
        pytest.fail("BLOCKED: PostgreSQL required")
    if parsed.hostname not in ("localhost", "127.0.0.1", "::1") or not parsed.path.endswith("_l2_e2e"):
        pytest.fail("BLOCKED: unsafe database target")
    if os.getenv("MCIAS_L2_ALLOW_ISOLATED_TESTS") != "YES":
        pytest.fail("BLOCKED: missing explicit test authorization")
    eng = create_engine(url, pool_pre_ping=True)
    with eng.connect() as c:
        if c.execute(text("select current_database()")).scalar_one() != parsed.path.lstrip("/"):
            pytest.fail("BLOCKED: actual database name mismatch")
        for table in ("users", "organizations", "audit_log"):
            if not c.execute(text("select to_regclass(:table)"), {"table": "public." + table}).scalar_one():
                pytest.fail("BLOCKED: required pre-migrated schema missing")
    yield eng
    eng.dispose()

@pytest.mark.parametrize("kind", ("permission", "organization"))
def test_denial_does_not_commit_pending_business_change(engine, kind):
    actor_id = os.environ.get("MCIAS_L2_SYNTHETIC_ACTOR_ID")
    org_id = os.environ.get("MCIAS_L2_SYNTHETIC_ORGANIZATION_ID")
    if not actor_id or not org_id:
        pytest.fail("BLOCKED: L1 synthetic disposable fixture not configured")
    marker = "L2-SEC-001-" + uuid.uuid4().hex
    with Session(engine) as setup:
        actor = setup.get(User, actor_id)
        org = setup.get(Organization, org_id)
        assert actor and actor.active and actor.organization_id == org_id and org
        assert org.name.startswith("L2-SYNTHETIC-"), "BLOCKED: refusing non-disposable fixture"
        original = org.name
        old_events = set(setup.scalars(text("select id from audit_log where actor_id = :id"), {"id": actor_id}).all())
    observed = None
    denial_count = None
    try:
        with Session(engine) as business:
            actor = business.get(User, actor_id)
            org = business.get(Organization, org_id)
            org.name = marker
            with pytest.raises(HTTPException) as caught:
                if kind == "permission":
                    require_permission(business, actor, "l2.sec001.never_grant")
                else:
                    require_organization(business, actor, org_id, "l2.sec001.never_grant")
            assert caught.value.status_code == 403
            # IMPORTANT: independent observation BEFORE any rollback to expose premature commit.
            with Session(engine) as reader:
                observed = reader.get(Organization, org_id).name
                denial_count = reader.execute(text(
                    "select count(*) from audit_log where actor_id=:id and action=:action"
                ), {"id": actor_id, "action": "permission_denied" if kind == "permission" else "tenant_access_denied"}).scalar_one()
            # Session close performs rollback only for truly uncommitted work.
    finally:
        # An isolated, synthetic disposable fixture only: restore any leaked commit.
        with Session(engine) as cleanup:
            obj = cleanup.get(Organization, org_id)
            if obj and obj.name == marker:
                obj.name = original
                cleanup.commit()
    assert observed == original, "FAIL: original guard committed pending business update"
    assert denial_count >= 1, "FAIL: denial audit not independently visible"
