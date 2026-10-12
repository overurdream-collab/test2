from uuid import uuid4
from sqlalchemy.orm import Session
from mcias.models import Permission

def test_permissions_catalog_is_exactly_approved_94_and_paginated(api):
    with Session(api.engine) as db:
        db.add(Permission(code="legacy.unapproved.read")); db.commit()
    response = api.client.get("/api/v1/permissions?limit=100", headers=api.headers["admin"])
    assert response.status_code == 200
    assert len(response.json()["items"]) == 94 and not response.json()["has_more"]
    assert all(p["code"] != "legacy.unapproved.read" for p in response.json()["items"])

def test_me_requires_authentication_only_and_describes_own_context(api):
    for name in ("none", "admin", "root"):
        response = api.client.get("/api/v1/permissions/me", headers=api.headers[name])
        assert response.status_code == 200, response.text
        assert response.json()["user"]["id"] == api.ids[name]
        assert response.json()["technical_rbac_admin"] == (name == "root")
    assert api.client.get("/api/v1/permissions/me", headers=api.headers["none"]).json()["permission_codes"] == []

def test_get_permission_uses_uuid_and_returns_404_for_absent_catalog(api):
    response = api.client.get(f"/api/v1/permissions/{api.permissions['claims.read']}", headers=api.headers["admin"])
    assert response.status_code == 200 and response.json()["code"] == "claims.read"
    assert api.client.get(f"/api/v1/permissions/{uuid4()}", headers=api.headers["admin"]).status_code == 404
    assert api.client.get("/api/v1/permissions/not-a-uuid", headers=api.headers["admin"]).status_code == 422
