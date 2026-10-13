from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.models import Group, GroupPermission, UserGroup

def test_list_groups_scopes_and_paginates(api):
    result = api.client.get("/api/v1/groups?limit=3", headers=api.headers["root"])
    assert result.status_code == 200 and len(result.json()["items"]) == 3 and result.json()["has_more"]
    assert all(g["organization_id"] == api.organization_id for g in result.json()["items"])

def test_create_group_has_audited_defaults_and_rejects_duplicate(api):
    payload = {"code": "custom_test", "name_ar": "فئة اختبار"}
    response = api.client.post("/api/v1/groups", json=payload, headers=api.headers["root"])
    assert response.status_code == 201, response.text
    with Session(api.engine) as db:
        group = db.get(Group, response.json()["id"])
        assert group.created_by == api.ids["root"] and not group.is_system
    assert api.client.post("/api/v1/groups", json=payload, headers=api.headers["root"]).status_code == 409

def test_get_group_contains_bounded_current_members_and_permissions(api):
    path = f"/api/v1/groups/{api.groups['viewer']}"
    response = api.client.get(path + "?permission_limit=2&member_limit=1", headers=api.headers["root"])
    assert response.status_code == 200, response.text
    assert response.json()["members"]["items"] == [api.ids["viewer"]]
    assert len(response.json()["permission_ids"]["items"]) == 2 and response.json()["permission_ids"]["has_more"]
    assert api.client.get(f"/api/v1/groups/{uuid4()}", headers=api.headers["root"]).status_code == 404

def test_close_group_disables_effective_grants_without_deleting_links(api):
    response = api.client.post(f"/api/v1/groups/{api.groups['viewer']}/close", json={"reason": "إغلاق اختباري"}, headers=api.headers["root"])
    assert response.status_code == 200 and response.json()["status"] == "closed"
    assert api.client.get("/api/v1/users", headers=api.headers["viewer"]).status_code == 403
    with Session(api.engine) as db:
        assert db.scalar(select(UserGroup.id).where(UserGroup.group_id == api.groups["viewer"]))

def test_add_member_scopes_target_and_rejects_duplicate(api):
    path = f"/api/v1/groups/{api.groups['viewer']}/members"
    payload = {"user_id": api.ids["none"]}
    result = api.client.post(path, json=payload, headers=api.headers["admin"])
    assert result.status_code == 201, result.text
    assert api.client.post(path, json=payload, headers=api.headers["admin"]).status_code == 409
    assert api.client.post(path, json={"user_id": api.ids["other"]}, headers=api.headers["admin"]).status_code == 404

def test_remove_member_closes_and_removes_access(api):
    path = f"/api/v1/groups/{api.groups['viewer']}/members/{api.ids['viewer']}/remove"
    response = api.client.post(path, json={"reason": "انتهاء العضوية"}, headers=api.headers["admin"])
    assert response.status_code == 200 and response.json()["status"] == "closed"
    assert api.client.get("/api/v1/users", headers=api.headers["viewer"]).status_code == 403

def test_grant_group_permission_is_persisted(api):
    from mcias.services.rbac_provisioning import preview_configuration
    from tests.authorization_fixtures import signed_fixture
    group = api.client.post("/api/v1/groups", json={"code": "test_grant", "name_ar": "اختبار"}, headers=api.headers["root"])
    assert group.status_code == 201
    with Session(api.engine) as db:
        plan=preview_configuration(db,api.organization_id,group.json()['id'],[api.permissions['claims.read']])
        envelope=signed_fixture(db,api.ids['root'],plan)
    response=api.client.post('/api/v1/admin/rbac/apply',json=envelope,headers=api.headers['root'])
    assert response.status_code==201,response.text
    with Session(api.engine) as db:
        assert db.get(GroupPermission,plan['groups'][0]['permissions'][0]['id']).granted_by==api.ids['root']


def test_revoke_group_permission_disables_inherited_grant(api):
    path = f"/api/v1/groups/{api.groups['viewer']}/permissions/{api.permissions['users.read']}/revoke"
    response = api.client.post(path, json={"reason": "سحب"}, headers=api.headers["root"])
    assert response.status_code == 200 and response.json()["status"] == "closed"
    assert api.client.get("/api/v1/users", headers=api.headers["viewer"]).status_code == 403
