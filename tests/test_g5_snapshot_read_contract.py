"""Read the official vocabulary through the existing authenticated snapshot API."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from mcias.audit_api import get_snapshot
from mcias.models import Base, Organization, Permission, Role, RolePermission, SessionToken, User, UserRole
from mcias.models_audit import AuditSnapshot
from test_shared_audit_inputs_pg16 import _seed


@pytest.fixture
def readable():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    org_id, actor_id, _, details = _seed(engine)
    with Session(engine) as db:
        permission, role = Permission(code="claims.read"), Role(code="synthetic-reader")
        db.add_all([permission, role]); db.flush()
        db.add_all([RolePermission(role_id=role.id, permission_id=permission.id),
                    UserRole(user_id=actor_id, role_id=role.id)])
        foreign = Organization(name="SYN-OTHER")
        db.add(foreign); db.flush()
        outsider = User(organization_id=foreign.id, username="SYN-other", password_hash="synthetic")
        db.add(outsider); db.flush()
        for token, user_id in (("SYN-session", actor_id), ("SYN-foreign", outsider.id)):
            db.add(SessionToken(user_id=user_id, token_hash=sha256(token.encode()).hexdigest(),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        db.commit()
        yield db, details["audit_snapshot_id"]
    engine.dispose()


def test_legacy_api_projection_keeps_original_and_does_not_invent_reason(readable):
    db, snapshot_id = readable
    original = db.get(AuditSnapshot, snapshot_id).findings
    result = get_snapshot(snapshot_id, authorization="Bearer SYN-session", db=db)
    assert result["findings"]["audit_state"] == "UNRESOLVED"
    assert result["findings"]["source_audit_state_schema_version"] == 1
    # The legacy seed has a persisted reference gap, so the reason is evidenced.
    assert result["findings"]["reason_code"] == "REFERENCE_INCOMPLETE"
    db.expire_all()
    assert db.get(AuditSnapshot, snapshot_id).findings == original
    assert original["audit_state"] == "UNRESOLVED_OR_MISSING_REFERENCE"


def test_snapshot_read_still_requires_authentication_tenant_and_permission(readable):
    db, snapshot_id = readable
    for token, expected in ((None, 401), ("Bearer SYN-invalid", 401), ("Bearer SYN-foreign", 404)):
        with pytest.raises(HTTPException) as denied:
            get_snapshot(snapshot_id, authorization=token, db=db)
        assert denied.value.status_code == expected
    role = db.scalar(select(Role).where(Role.code == "synthetic-reader"))
    db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
    db.commit()
    with pytest.raises(HTTPException) as denied:
        get_snapshot(snapshot_id, authorization="Bearer SYN-session", db=db)
    assert denied.value.status_code == 403
