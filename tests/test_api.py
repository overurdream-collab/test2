from fastapi.testclient import TestClient
from mcias.app import app, get_settings

class TestSettings:
    environment = "development"
    bootstrap_token = "local-test-token"

app.dependency_overrides[get_settings] = lambda: TestSettings()
client = TestClient(app)

def test_liveness():
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_status_denied_by_default():
    assert client.get("/api/v1/system/status").status_code == 403

def test_status_authorized_only_with_dev_token():
    r = client.get("/api/v1/system/status", headers={"X-Bootstrap-Token": "local-test-token"})
    assert r.status_code == 200
    assert r.json()["production_ready"] is False
