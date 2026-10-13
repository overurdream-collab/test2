from datetime import date
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.models import AuditLog, User, UserGroup, UserPermission
from mcias.security import verify_password

def test_list_users_is_paginated_and_tenant_bound(api):
    response = api.client.get("/api/v1/users?limit=2", headers=api.headers["admin"])
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2 and response.json()["has_more"]
    assert all(u["organization_id"] == api.organization_id for u in response.json()["items"])
    assert response.headers["cache-control"] == "no-store"
    assert api.client.get("/api/v1/users?limit=101", headers=api.headers["admin"]).status_code == 422

def test_create_user_commits_hash_and_audit_without_secret_response(api):
    payload = {"username": "SYN-created", "password": api.password, "full_name_ar": "مستخدم اختباري"}
    response = api.client.post("/api/v1/users", json=payload, headers=api.headers["admin"])
    assert response.status_code == 201, response.text
    assert "password" not in response.text and "password_hash" not in response.text
    with Session(api.engine) as db:
        user = db.get(User, response.json()["id"])
        assert user.organization_id == api.organization_id
        assert user.active and not user.is_super_admin and verify_password(api.password, user.password_hash)
        record = db.scalar(select(AuditLog).where(AuditLog.action == "user.create", AuditLog.resource_id == user.id))
        assert record and record.actor_id == api.ids["admin"]
        assert api.password not in str(record.after_state)
    assert api.client.post("/api/v1/users", json=payload, headers=api.headers["admin"]).status_code == 409

def test_get_user_masks_cross_tenant_and_missing_identifiers(api):
    assert api.client.get(f"/api/v1/users/{api.ids['none']}", headers=api.headers["admin"]).status_code == 200
    for identifier in (api.ids["other"], str(uuid4())):
        assert api.client.get(f"/api/v1/users/{identifier}", headers=api.headers["admin"]).status_code == 404

def test_close_user_invalidates_existing_session_and_is_not_reopenable(api):
    path = f"/api/v1/users/{api.ids['none']}/close"
    result = api.client.post(path, json={"reason": "نهاية الاختبار"}, headers=api.headers["admin"])
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "closed" and not result.json()["active"]
    assert result.json()["effective_to"] == str(date.today())
    assert api.client.get("/api/v1/permissions/me", headers=api.headers["none"]).status_code == 401
    assert api.client.post(path, json={"reason": "مرة ثانية"}, headers=api.headers["admin"]).status_code == 409

def test_user_permissions_returns_effective_catalog(api):
    result = api.client.get(f"/api/v1/users/{api.ids['viewer']}/permissions?limit=100", headers=api.headers["admin"])
    assert result.status_code == 200
    codes = [p["code"] for p in result.json()["items"]]
    assert codes == sorted(set(codes)) and "users.read" in codes and "reports.medical.read" not in codes

def test_grant_user_permission_conflict_and_persistence(api):
    path=f"/api/v1/users/{api.ids['none']}/permissions"
    payload={'permission_id':api.permissions['claims.read']}
    assert api.client.post(path,json=payload,headers=api.headers['admin']).status_code==403
    assert api.client.post(path,json=payload,headers=api.headers['root']).status_code==409
    with Session(api.engine) as db:
        assert db.scalar(select(UserPermission.id).where(UserPermission.user_id==api.ids['none'])) is None


def test_revoke_user_permission_closes_without_delete(api):
    # Historical individual grants remain inspectable and revocable, never active.
    permission_id=api.permissions['users.read']
    with Session(api.engine) as db:
        record=UserPermission(organization_id=api.organization_id,user_id=api.ids['none'],permission_id=permission_id,granted_by=api.ids['root'],effective_from=date.today())
        db.add(record);db.commit();record_id=record.id
    assert api.client.get('/api/v1/users',headers=api.headers['none']).status_code==403
    response=api.client.post(f"/api/v1/users/{api.ids['none']}/permissions/{permission_id}/revoke",json={'reason':'سحب تاريخي'},headers=api.headers['root'])
    assert response.status_code==200,response.text
    with Session(api.engine) as db:assert db.get(UserPermission,record_id).status=='closed'


def test_group_transfer_is_atomic_if_destination_membership_conflicts(api):
    user_id = api.ids["none"]
    source, destination = api.groups["viewer"], api.groups["reporter"]
    for group_id in (source, destination):
        response = api.client.post(f"/api/v1/groups/{group_id}/members", json={"user_id": user_id}, headers=api.headers["admin"])
        assert response.status_code == 201
    path = f"/api/v1/users/{user_id}/group-transfers"
    payload = {"from_group_id": source, "to_group_id": destination, "reason": "نقل"}
    assert api.client.post(path, json=payload, headers=api.headers["admin"]).status_code == 409
    with Session(api.engine) as db:
        assert db.scalar(select(UserGroup.status).where(UserGroup.user_id == user_id, UserGroup.group_id == source)) == "open"
    payload["to_group_id"] = api.groups["auditor"]
    result = api.client.post(path, json=payload, headers=api.headers["admin"])
    assert result.status_code == 200 and result.json()["group_id"] == api.groups["auditor"]
