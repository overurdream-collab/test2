from fastapi.testclient import TestClient
from mcias.app import app

def test_security_headers_on_public_health_endpoint():
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors" in response.headers["content-security-policy"]

def test_sensitive_report_routes_disable_caching_without_disclosing_data():
    response = TestClient(app).get("/api/v1/reports/snapshots/not-found")
    assert response.status_code in (401, 403, 404)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
