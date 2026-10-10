"""G5 API approval endpoints deny unauthenticated requests."""
from fastapi.testclient import TestClient
from mcias.app import app

def test_g5_grant_enrollment_requires_authentication():
    response=TestClient(app).post("/api/v1/audit-policies/grants",json={
        "organization_id":"org","policy_id":"p",
        "policy_fingerprint":"a"*64,"approver_id":"a","reviewer_id":"b",
        "signature":"b"*64})
    assert response.status_code==401

def test_g5_grant_revocation_requires_authentication():
    response=TestClient(app).post("/api/v1/audit-policies/grants/test/revoke")
    assert response.status_code==401
