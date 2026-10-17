"""Synthetic HTTP RBAC, no cross-tenant access or accidental activation."""
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from mcias.app import app, get_db
from mcias.models import Base, Organization, User, Role, UserRole, Permission, RolePermission
from mcias.models_reference_points import ReferencePoint
import mcias.reference_points_api as api


@pytest.fixture
def scoped_client(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        home = Organization(name="synthetic-home")
        foreign = Organization(name="synthetic-foreign")
        db.add_all([home, foreign])
        db.flush()
        actor = User(username="syn-points-readonly", password_hash="unused",
                     organization_id=home.id)
        owner = User(username="syn-points-foreign", password_hash="unused",
                     organization_id=foreign.id)
        db.add_all([actor, owner])
        db.flush()
        role = Role(code="synthetic-point-reader")
        permission = Permission(code="reference.read")
        db.add_all([role, permission])
        db.flush()
        db.add_all([UserRole(user_id=actor.id, role_id=role.id),
                    RolePermission(role_id=role.id, permission_id=permission.id)])
        point = ReferencePoint(
            organization_id=foreign.id, section="tariffs", logical_key="H2:CONSULT",
            version=1, title="Other institution tariff",
            clause_text="Not accessible to home institution", rule_type="amount",
            provider_code="H2", service_code="CONSULT", amount="9000",
            currency="YER", effective_from=date(2026, 1, 1),
            effective_until=date(2028, 1, 1), status="approved",
            created_by=owner.id, approved_by=owner.id
        )
        db.add(point)
        db.commit()
        actor_id, foreign_id = actor.id, point.id

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(api, "resolve_user",
                        lambda db, bearer: (db.get(User, actor_id), None))
    try:
        yield TestClient(app), foreign_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_cross_organization_point_is_never_listed_or_read(scoped_client):
    client, other_id = scoped_client
    resp = client.get("/api/v1/reference-points?section=tariffs")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert client.get("/api/v1/reference-points/" + other_id).status_code == 404


def test_reference_point_write_and_approval_need_separate_permissions(scoped_client):
    client, foreign_id = scoped_client
    proposal = dict(section="tariffs", logical_key="H1:CONSULT",
                    title="Synthetic", clause_text="Test source price",
                    rule_type="amount", provider_code="H1", service_code="CONSULT",
                    amount="5000", currency="YER",
                    effective_from="2026-01-01", effective_until="2028-01-01")
    assert client.post("/api/v1/reference-points", json=proposal).status_code == 403
    assert client.post("/api/v1/reference-points/" + foreign_id + "/approve",
        json={"authorization_id": "fake", "reason": "Synthetic rationale longer than twenty characters"}).status_code == 403


def test_invalid_section_does_not_return_other_tenant_data(scoped_client):
    client, _ = scoped_client
    assert client.get("/api/v1/reference-points?section=unknown").status_code == 409
