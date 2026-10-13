import logging
from uuid import UUID, uuid4
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from mcias.models import AuditLog, User

def http_events(api):
    with Session(api.engine) as db:
        return list(db.scalars(select(AuditLog).where(AuditLog.action == "http.request")))

def test_successful_get_is_not_audited_but_errors_are(api):
    assert api.client.get("/api/v1/users", headers=api.headers["admin"]).status_code == 200
    assert http_events(api) == []
    assert api.client.get("/api/v1/users").status_code == 401
    assert api.client.get("/api/v1/users", headers=api.headers["none"]).status_code == 403
    assert api.client.get(f"/api/v1/users/{uuid4()}", headers=api.headers["admin"]).status_code == 404
    events = http_events(api)
    assert len(events) == 3 and {r.error_code for r in events} == {"HTTP_401", "HTTP_403", "HTTP_404"}
    assert all(r.request_id and r.category == "http_access" for r in events)

def test_mutation_service_and_http_events_are_distinct_and_redacted(api):
    payload = {"username": "SYN-audit-check", "password": api.password}
    response = api.client.post("/api/v1/users?private=SYN-query-secret", json=payload, headers=api.headers["admin"])
    assert response.status_code == 201
    UUID(response.headers["x-request-id"])
    events = http_events(api)
    assert len(events) == 1
    event = events[0]
    assert event.actor_id == api.ids["admin"] and event.organization_id == api.organization_id
    assert event.result == "success" and event.endpoint == "/api/v1/users"
    assert event.request_id == response.headers["x-request-id"] and event.details == {"status_code": 201}
    serialized = str(vars(event))
    assert api.password not in serialized and "SYN-query-secret" not in serialized and "Bearer" not in serialized
    with Session(api.engine) as db:
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "user.create", AuditLog.resource_id == response.json()["id"])) == 1

def test_validation_error_is_audited_without_body(api):
    response = api.client.post("/api/v1/users", json={"username": "SYN-invalid", "password": "short"}, headers=api.headers["admin"])
    assert response.status_code == 422
    event = http_events(api)[0]
    assert event.error_code == "HTTP_422" and event.error_message is None
    assert "short" not in str(vars(event))

def test_auxiliary_audit_failure_preserves_original_http_result(api, monkeypatch, caplog):
    from mcias.middleware import audit
    def unavailable():
        raise RuntimeError("SYN-private-DB-detail")
        yield
    monkeypatch.setattr(audit, "open_db", unavailable)
    with caplog.at_level(logging.ERROR):
        response = api.client.post("/api/v1/groups", json={"code": "audit_failure", "name_ar": "اختبار"}, headers=api.headers["root"])
    assert response.status_code == 201
    assert "HTTP audit persistence unavailable" in caplog.text and "SYN-private-DB-detail" not in caplog.text

def test_failed_business_commit_returns_503_and_rolls_back(api, monkeypatch):
    original = Session.commit
    def fail_business_commit(db):
        if any(isinstance(row, User) and row.username == "SYN-commit-fails" for row in db.identity_map.values()):
            raise OperationalError("SYN-private-SQL", {}, RuntimeError("SYN-private-DB-detail"))
        return original(db)
    monkeypatch.setattr(Session, "commit", fail_business_commit)
    response = api.client.post("/api/v1/users", json={"username": "SYN-commit-fails", "password": api.password}, headers=api.headers["root"])
    assert response.status_code == 503, response.text
    assert "SYN-private" not in response.text
    with Session(api.engine) as db:
        assert db.scalar(select(User.id).where(User.username == "SYN-commit-fails")) is None
        assert db.scalar(select(AuditLog.id).where(AuditLog.action == "user.create")) is None

def test_rate_limiter_still_enforces_429_and_access_audit(api):
    for _ in range(100):
        assert api.client.get("/api/v1/permissions/me", headers=api.headers["none"]).status_code == 200
    response = api.client.get("/api/v1/permissions/me", headers=api.headers["none"])
    assert response.status_code == 429 and int(response.headers["retry-after"]) >= 1
    assert any(r.error_code == "HTTP_429" for r in http_events(api))
