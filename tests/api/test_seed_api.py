import os
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from mcias.models import AuditLog, Group, Permission, UserGroup

def test_seed_requires_existing_super_role_and_mfa_and_is_idempotent(api_factory):
    api = api_factory(seed=False)
    for name in ("none", "flag_only", "no_mfa"):
        assert api.client.post("/api/v1/rbac/seed", headers=api.headers[name]).status_code == 403
    response = api.client.post("/api/v1/rbac/seed", headers=api.headers["root"])
    assert response.status_code == 200, response.text
    assert response.json() == {"permissions_created": 94, "groups_created": 8, "group_permissions_created": 156}
    assert api.client.post("/api/v1/rbac/seed", headers=api.headers["root"]).json() == {
        "permissions_created": 0, "groups_created": 0, "group_permissions_created": 0}
    with Session(api.engine) as db:
        assert db.scalar(select(func.count()).select_from(Group).where(Group.organization_id == api.other_organization_id)) == 0
        assert db.scalar(select(func.count()).select_from(UserGroup)) == 0

def test_seed_rejects_client_actor_and_organization_fields(api):
    assert api.client.post("/api/v1/rbac/seed", json={"organization_id": api.other_organization_id, "created_by": api.ids["root"]}, headers=api.headers["root"]).status_code == 422
    assert api.client.post("/api/v1/rbac/seed", headers=api.headers["admin"]).status_code == 403

@pytest.mark.skipif(not os.getenv("MCIAS_RBAC_API_DATABASE_URL"), reason="isolated PostgreSQL RBAC API database required")
def test_real_postgres_api_commit_and_triggered_audit_hash(api_factory):
    api = api_factory(seed=False, url=os.environ["MCIAS_RBAC_API_DATABASE_URL"])
    assert api.client.post("/api/v1/rbac/seed", headers=api.headers["root"]).status_code == 200
    user = api.client.post("/api/v1/users", json={"username": "SYN-api-pg-" + api.ids["none"], "password": api.password}, headers=api.headers["root"])
    assert user.status_code == 201, user.text
    group = api.client.post("/api/v1/groups", json={"code": "pg_api_test", "name_ar": "فئة اختبار PostgreSQL"}, headers=api.headers["root"])
    assert group.status_code == 201, group.text
    with Session(api.engine) as db:
        permission_id = db.scalar(select(Permission.id).where(Permission.code == "users.read"))
    path = f"/api/v1/groups/{group.json()['id']}"
    assert api.client.post(path + "/permissions", json={"permission_id": permission_id}, headers=api.headers["root"]).status_code == 201
    assert api.client.post(path + "/members", json={"user_id": user.json()["id"]}, headers=api.headers["root"]).status_code == 201
    assert api.client.post(path + f"/members/{user.json()['id']}/remove", json={"reason": "اختبار الإغلاق"}, headers=api.headers["root"]).status_code == 200
    with Session(api.engine) as db:
        audits = list(db.scalars(select(AuditLog).where(AuditLog.organization_id == api.organization_id)))
        assert any(record.action == "http.request" for record in audits)
        assert all(record.hash and len(record.hash) == 64 for record in audits)
