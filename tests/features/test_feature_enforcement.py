from sqlalchemy.orm import Session
from mcias.models import Role, RolePermission, UserRole
from mcias.services import feature_service as f

def test_legacy_rollout_guard_revokes_direct_api_access(features_api, monkeypatch):
    a=features_api;monkeypatch.setenv("MCIAS_FEATURE_ENFORCEMENT","true")
    # Legacy routes keep their own RBAC; an entitlement alone never grants it.
    with Session(a.engine) as db:
        role=Role(code="feature-legacy-reader");db.add(role);db.flush()
        db.add(UserRole(user_id=a.ids["admin"],role_id=role.id))
        db.add(RolePermission(role_id=role.id,permission_id=a.permissions["claims.read"]));db.commit()
    url="/api/v1/workspace/catalog/claims"
    assert a.client.get(url,headers=a.headers["admin"]).status_code==403
    with Session(a.engine) as db:
        f.grant_feature(db,a.organization_id,"claims.list",a.ids["root"]);db.commit()
    assert a.client.get(url,headers=a.headers["admin"]).status_code==200
    with Session(a.engine) as db:
        f.revoke_feature(db,a.organization_id,"claims.list",a.ids["root"],"Test revocation");db.commit()
    assert a.client.get(url,headers=a.headers["admin"]).status_code==403
    assert a.client.get(url).status_code==401

def test_new_features_context_does_not_require_legacy_profile_permission(features_api):
    a=features_api
    response=a.client.get("/api/v1/me/features",headers=a.headers["admin"])
    assert response.status_code==200
    assert "reference.contracts.read" in response.json()["permissions"]
    assert response.json()["features"]==[]

def test_temporal_rbac_read_bridge_does_not_require_legacy_role_grants(features_api):
    a=features_api;path="/api/v1/feature-data/catalog/claims"
    assert a.client.get(path,headers=a.headers["admin"]).status_code==403
    with Session(a.engine) as db:
        f.grant_feature(db,a.organization_id,"claims.list",a.ids["root"]);db.commit()
    assert a.client.get(path,headers=a.headers["admin"]).status_code==200
    assert a.client.get(path,headers=a.headers["none"]).status_code==403
    assert a.client.get(path,headers=a.headers["other"]).status_code==403
