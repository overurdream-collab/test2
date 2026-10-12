import pytest

@pytest.mark.parametrize("path", ["/api/v1/admin/features", "/api/v1/admin/features/tree", "/api/v1/admin/feature-organizations"])
def test_admin_reads_require_authenticated_mfa_super_admin(features_api, path):
    a = features_api
    assert a.client.get(path).status_code == 401
    for name in ("admin", "viewer", "flag_only", "no_mfa"):
        assert a.client.get(path, headers=a.headers[name]).status_code == 403
    assert a.client.get(path, headers=a.headers["root"]).status_code == 200

def test_feature_grant_revoke_and_same_org_read(features_api):
    a = features_api; base = f"/api/v1/organizations/{a.organization_id}/features"
    assert a.client.post(base + "/inputs.contracts/grant", headers=a.headers["admin"]).status_code == 403
    response = a.client.post(base + "/inputs.contracts/grant", headers=a.headers["root"])
    assert response.status_code == 201
    assert a.client.post(base + "/inputs.contracts/grant", headers=a.headers["root"]).status_code == 409
    assert a.client.get(base, headers=a.headers["other"]).status_code == 404
    mine = a.client.get("/api/v1/me/features", headers=a.headers["admin"])
    assert mine.json()["features"] == ["inputs.contracts"]
    assert mine.headers["cache-control"] == "no-store"
    assert a.client.post(base + "/inputs.contracts/revoke", json={"reason": "Test revoke"}, headers=a.headers["root"]).status_code == 200
    assert a.client.get("/api/v1/me/features", headers=a.headers["admin"]).json()["features"] == []

def test_batch_is_atomic_and_rejects_stale_revision(features_api):
    a = features_api; base = f"/api/v1/organizations/{a.organization_id}/features"
    state = a.client.get(base, headers=a.headers["root"]).json()
    payload = {"codes": ["inputs.contracts", "beneficiaries.names"], "expected_revision": state["revision"]}
    assert a.client.put(base, json=payload, headers=a.headers["root"]).status_code == 200
    assert a.client.put(base, json=payload, headers=a.headers["root"]).status_code == 409
    current = a.client.get(base, headers=a.headers["root"]).json()
    assert len(current["items"]) == 2
    assert a.client.put(base, json={"codes": [], "expected_revision": current["revision"]}, headers=a.headers["root"]).status_code == 409
    assert len(a.client.get(base, headers=a.headers["root"]).json()["items"]) == 2

def test_super_admin_management_is_not_cross_tenant_data_access(features_api):
    a = features_api
    base = f"/api/v1/organizations/{a.other_organization_id}/features"
    assert a.client.post(base + "/inputs.contracts/grant", headers=a.headers["root"]).status_code == 201
    assert a.client.get("/api/v1/me/features", headers=a.headers["admin"]).json()["features"] == []
    assert a.client.post(base + "/inputs/grant", headers=a.headers["root"]).status_code == 409

def test_grant_ids_and_actor_cannot_be_supplied(features_api):
    a = features_api; base = f"/api/v1/organizations/{a.organization_id}/features"
    response = a.client.put(base, headers=a.headers["root"], json={"codes": [], "expected_revision": "0" * 64, "granted_by": a.ids["admin"]})
    assert response.status_code == 422
