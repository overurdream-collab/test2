from fastapi.testclient import TestClient
from mcias.app import app

def test_security_headers_on_public_health_endpoint():
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors" in response.headers["content-security-policy"]
