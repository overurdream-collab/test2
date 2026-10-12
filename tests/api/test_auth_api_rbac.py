from datetime import date, datetime, timedelta, timezone
import time
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.mfa import generate_totp
from mcias.models import GroupPermission, SessionToken, User, UserPermission
from mcias.services.user_lifecycle import grant_user_permission

@pytest.mark.parametrize("path", ["/api/v1/users", "/api/v1/groups", "/api/v1/permissions", "/api/v1/permissions/me"])
def test_read_authentication_required(api, path):
    assert api.client.get(path).status_code == 401

@pytest.mark.parametrize("method,path,payload", [
    ("POST", "/api/v1/users", {"username": "SYN-denied", "password": "SYN-password-long"}),
    ("POST", "/api/v1/groups", {"code": "denied", "name_ar": "ممنوع"}),
    ("POST", "/api/v1/rbac/seed", {}),
    ("GET", "/api/v1/users", None),
    ("GET", "/api/v1/groups", None),
    ("GET", "/api/v1/permissions", None),
])
def test_missing_permission_is_403(api, method, path, payload):
    assert api.client.request(method, path, json=payload, headers=api.headers["none"]).status_code == 403

def test_real_super_admin_login_requires_password_and_mfa(api):
    payload = {"username": api.root_username, "password": api.password}
    assert api.client.post("/api/v1/auth/login", json=payload).status_code == 401
    payload["totp_code"] = generate_totp(api.mfa_secret, int(time.time()) // 30)
    response = api.client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    result = api.client.get("/api/v1/permissions/me", headers={"Authorization": "Bearer " + token})
    assert result.status_code == 200 and result.json()["technical_rbac_admin"]
    assert api.client.post("/api/v1/auth/login", json=payload).status_code == 401

@pytest.mark.parametrize("condition", ["expired", "revoked", "inactive", "closed", "future"])
def test_invalid_or_non_effective_sessions_rejected(api, condition):
    user_id = api.ids["future"] if condition == "future" else api.ids["none"]
    with Session(api.engine) as db:
        user = db.get(User, user_id)
        session = db.scalar(select(SessionToken).where(SessionToken.user_id == user_id))
        if condition == "expired": session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        if condition == "revoked": session.revoked_at = datetime.now(timezone.utc)
        if condition == "inactive": user.active = False
        if condition == "closed": user.status, user.effective_to = "closed", date.today()
        db.commit()
    assert api.client.get("/api/v1/permissions/me", headers=api.headers["future" if condition == "future" else "none"]).status_code == 401

def test_super_admin_flag_does_not_grant_bootstrap_or_technical_rights(api):
    assert api.client.get("/api/v1/users", headers=api.headers["flag_only"]).status_code == 403
    assert api.client.post("/api/v1/rbac/seed", headers=api.headers["flag_only"]).status_code == 403
    assert api.client.get("/api/v1/permissions/me", headers=api.headers["flag_only"]).json()["technical_rbac_admin"] is False

def test_privileged_account_cannot_be_managed_by_institution_admin(api):
    path = f"/api/v1/users/{api.ids['root']}/close"
    assert api.client.post(path, json={"reason": "غير مسموح"}, headers=api.headers["admin"]).status_code == 403

def test_delegation_cannot_escalate_or_assign_platform_permissions(api):
    with Session(api.engine) as db:
        grant_user_permission(db, api.ids["limited"], api.permissions["users.permissions.grant"], api.ids["root"])
        db.commit()
    path = f"/api/v1/users/{api.ids['limited']}/permissions"
    assert api.client.post(path, json={"permission_id": api.permissions["claims.approve"]}, headers=api.headers["limited"]).status_code == 403
    for name in ("root", "admin"):
        assert api.client.post(path, json={"permission_id": api.permissions["system.configure"]}, headers=api.headers[name]).status_code == 403

def test_future_group_grants_are_checked_before_delegation(api):
    group = api.client.post("/api/v1/groups", json={"code": "future_grants", "name_ar": "فئة مستقبلية"}, headers=api.headers["root"])
    assert group.status_code == 201
    with Session(api.engine) as db:
        grant_user_permission(db, api.ids["limited"], api.permissions["groups.members.add"], api.ids["root"])
        db.add(GroupPermission(organization_id=api.organization_id, group_id=group.json()["id"],
            permission_id=api.permissions["claims.approve"], effective_from=date.today() + timedelta(days=1), granted_by=api.ids["root"]))
        db.commit()
    assert api.client.post(f"/api/v1/groups/{group.json()['id']}/members", json={"user_id": api.ids["none"]}, headers=api.headers["limited"]).status_code == 403

def test_future_individual_grant_is_not_effective(api):
    with Session(api.engine) as db:
        db.add(UserPermission(organization_id=api.organization_id, user_id=api.ids["none"],
            permission_id=api.permissions["users.read"], effective_from=date.today() + timedelta(days=1), granted_by=api.ids["root"]))
        db.commit()
    assert api.client.get("/api/v1/users", headers=api.headers["none"]).status_code == 403

@pytest.mark.parametrize("spoof", [{"organization_id": "other"}, {"created_by": "other"}, {"is_super_admin": True}, {"password_hash": "untrusted"}])
def test_user_input_cannot_spoof_trusted_fields(api, spoof):
    response = api.client.post("/api/v1/users", json={"username": "SYN-spoof", "password": api.password, **spoof}, headers=api.headers["admin"])
    assert response.status_code == 422 and api.password not in response.text

def test_password_validation_does_not_echo_sensitive_input(api):
    secret = "SYN-short"
    response = api.client.post("/api/v1/users", json={"username": "SYN-invalid", "password": secret}, headers=api.headers["admin"])
    assert response.status_code == 422 and secret not in response.text

def test_all_mutation_endpoints_reject_unprivileged_actor(api):
    user, group, permission = api.ids["viewer"], api.groups["viewer"], api.permissions["claims.read"]
    cases = [
        (f"/api/v1/users/{user}/close", {"reason": "اختبار"}),
        (f"/api/v1/users/{user}/permissions", {"permission_id": permission}),
        (f"/api/v1/users/{user}/permissions/{permission}/revoke", {"reason": "اختبار"}),
        (f"/api/v1/users/{user}/group-transfers", {"from_group_id": group, "to_group_id": api.groups["reporter"], "reason": "اختبار"}),
        (f"/api/v1/groups/{group}/close", {"reason": "اختبار"}),
        (f"/api/v1/groups/{group}/members", {"user_id": user}),
        (f"/api/v1/groups/{group}/members/{user}/remove", {"reason": "اختبار"}),
        (f"/api/v1/groups/{group}/permissions", {"permission_id": permission}),
        (f"/api/v1/groups/{group}/permissions/{permission}/revoke", {"reason": "اختبار"}),
    ]
    for path, payload in cases:
        assert api.client.post(path, json=payload, headers=api.headers["none"]).status_code == 403
