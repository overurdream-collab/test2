"""G3 HTTP negative tests: default-deny, tenant isolation, and write RBAC."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from mcias.app import app, get_db
from mcias.models import Base, Organization, User, Role, UserRole, Permission, RolePermission
import mcias.reference_api as api
from mcias.models_reference import ContractVersion
from datetime import date

@pytest.fixture
def client(monkeypatch):
    engine=create_engine("sqlite+pysqlite:///:memory:",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org1,org2=Organization(name="one"),Organization(name="two")
        user=User(username="g3-api",password_hash="fixture")
        db.add_all([org1,org2,user]);db.flush()
        user.organization_id=org1.id
        role=Role(code="g3-reader")
        permission=Permission(code="reference.read")
        db.add_all([role,permission]);db.flush()
        db.add_all([UserRole(user_id=user.id,role_id=role.id),
                    RolePermission(role_id=role.id,permission_id=permission.id)])
        foreign=ContractVersion(organization_id=org2.id,provider_code="H2",version=1,
            effective_from=date(2027,1,1),effective_until=date(2028,1,1),status="approved")
        db.add(foreign);db.commit()
        user_id=user.id
        foreign_id=foreign.id
    def dependency():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db]=dependency
    monkeypatch.setattr(api,"resolve_user",lambda db,header:(db.get(User,user_id),None))
    try:
        yield TestClient(app),foreign_id
    finally:
        app.dependency_overrides.pop(get_db,None)
        engine.dispose()

def test_cross_tenant_contract_impact_denied(client):
    http,foreign_id=client
    response=http.get("/api/v1/reference/contracts/"+foreign_id+"/impact")
    assert response.status_code==403

def test_read_only_actor_cannot_create_contract(client):
    http,_=client
    response=http.post("/api/v1/reference/contracts",json={
        "provider_code":"H1","effective_from":"2027-01-01",
        "effective_until":"2028-01-01","precedence":0})
    assert response.status_code==403

def test_read_only_actor_cannot_import_tariffs(client):
    http,foreign_id=client
    response=http.post("/api/v1/reference/contracts/"+foreign_id+"/tariffs/import",
        content=b"service_code,amount,currency\nS1,100,YER\n")
    assert response.status_code==403

def test_read_only_actor_cannot_approve_contract(client):
    http,foreign_id=client
    response=http.post("/api/v1/reference/contracts/"+foreign_id+"/approve")
    assert response.status_code==403
