from tests.authorization_fixtures import approve_fixture
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from mcias.app import app, get_db
from mcias.models import Organization, Base, User, Role, Permission, UserRole, RolePermission
from mcias.security import hash_password

@pytest.fixture
def client():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(username="synthetic-reviewer", password_hash=hash_password("synthetic-long-password")))
        db.commit()
    def override_db():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = override_db
    try:
        yield TestClient(app), engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

def test_login_logout_and_default_deny(client):
    api, engine = client
    assert api.post("/api/v1/auth/login", json={"username":"synthetic-reviewer","password":"invalid"}).status_code == 401
    response = api.post("/api/v1/auth/login", json={"username":"synthetic-reviewer","password":"synthetic-long-password"})
    assert response.status_code == 200
    header = {"Authorization":"Bearer " + response.json()["access_token"]}
    assert api.get("/api/v1/auth/me", headers=header).status_code == 403
    with Session(engine) as db:
        org=Organization(name="SYN-auth");db.add(org);db.flush()
        user = db.query(User).filter_by(username="synthetic-reviewer").one()
        user.organization_id=org.id
        role = Role(code="synthetic-viewer")
        permission = Permission(code="profile.read")
        db.add_all([role, permission])
        db.flush()
        db.add_all([UserRole(user_id=user.id, role_id=role.id), RolePermission(role_id=role.id, permission_id=permission.id)])
        db.flush();approve_fixture(db)
        db.commit()
    assert api.get("/api/v1/auth/me", headers=header).status_code == 200
    assert api.post("/api/v1/auth/logout", headers=header).status_code == 204
    assert api.get("/api/v1/auth/me", headers=header).status_code == 401

def test_missing_token_denied(client):
    api, _ = client
    assert api.get("/api/v1/auth/me").status_code == 401
    assert api.post("/api/v1/auth/logout").status_code == 401
