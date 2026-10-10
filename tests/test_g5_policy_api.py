import pytest
pytestmark = pytest.mark.usefixtures("limiter_database")
"""G5 API approval endpoints deny unauthenticated requests."""
from fastapi.testclient import TestClient
from mcias.app import app, get_settings
from mcias.config import Settings
import pytest

@pytest.fixture(autouse=True)
def local_settings():
    app.dependency_overrides[get_settings]=lambda: Settings(database_url="sqlite:///unused.db",bootstrap_token="test-only",environment="development")
    yield
    app.dependency_overrides.pop(get_settings,None)

def test_g5_grant_enrollment_requires_authentication():
    response=TestClient(app).post("/api/v1/audit-policies/grants",json={
        "organization_id":"org","policy_id":"p",
        "policy_fingerprint":"a"*64,"approver_id":"a","reviewer_id":"b",
        "signature":"b"*64})
    assert response.status_code==401

def test_g5_grant_revocation_requires_authentication():
    response=TestClient(app).post("/api/v1/audit-policies/grants/test/revoke")
    assert response.status_code==401
