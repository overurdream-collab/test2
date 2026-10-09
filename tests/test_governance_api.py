import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from mcias.app import app, get_db
from mcias.models import Base, User, Organization, Role, Permission, UserRole, RolePermission, RuleVersion, SourceFile, WrittenAuthorization, AuditLog
from mcias.security import hash_password
from datetime import datetime, timezone

@pytest.fixture
def env():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread":False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org = Organization(name="Synthetic")
        actor = User(username="operator", password_hash=hash_password("synthetic-long-password"))
        db.add_all([org, actor]); db.flush()
        rule = RuleVersion(organization_id=org.id, rule_type="exclusion")
        db.add(rule); db.commit()
        rule_id = rule.id
    def override():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = override
    try:
        yield TestClient(app), engine, rule_id
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

def test_t06_t07_default_deny_and_logged(env):
    client, engine, rule_id = env
    token = client.post("/api/v1/auth/login", json={"username":"operator","password":"synthetic-long-password"}).json()["access_token"]
    h = {"Authorization":"Bearer "+token}
    assert client.get("/api/v1/rules/exclusions/edit-permission", headers=h).status_code == 403
    assert client.post(f"/api/v1/rules/{rule_id}/activate", headers=h).status_code == 403
    with Session(engine) as db:
        assert db.query(AuditLog).filter_by(action="governance_denied").count() == 2
        assert db.get(RuleVersion, rule_id).status == "draft"

def test_t07_requires_distinct_active_approver(env):
    client, engine, rule_id = env
    with Session(engine) as db:
        org = db.query(Organization).first()
        actor = db.query(User).filter_by(username="operator").one()
        role = Role(code="activator")
        permission = Permission(code="rules.activate")
        db.add_all([role, permission]); db.flush()
        db.add_all([UserRole(user_id=actor.id, role_id=role.id), RolePermission(role_id=role.id, permission_id=permission.id)])
        source = SourceFile(sha256="b"*64, original_filename="authorization.pdf", storage_key="synthetic-auth")
        db.add(source); db.flush()
        authorization = WrittenAuthorization(organization_id=org.id, source_id=source.id, approved_by=actor.id, approved_at=datetime.now(timezone.utc))
        db.add(authorization); db.flush()
        db.get(RuleVersion, rule_id).written_authorization_id = authorization.id
        db.commit()
    token = client.post("/api/v1/auth/login", json={"username":"operator","password":"synthetic-long-password"}).json()["access_token"]
    h = {"Authorization":"Bearer "+token}
    assert client.post(f"/api/v1/rules/{rule_id}/activate", headers=h).status_code == 403
    with Session(engine) as db:
        org = db.query(Organization).first()
        approver = User(username="approver", password_hash="synthetic-only", organization_id=org.id)
        db.add(approver); db.flush()
        db.query(WrittenAuthorization).first().approved_by = approver.id
        db.commit()
    response = client.post(f"/api/v1/rules/{rule_id}/activate", headers=h)
    assert response.status_code == 200
    assert response.json()["status"] == "active"
