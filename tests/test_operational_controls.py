"""Security boundaries: atomic quotas, tenant archives, encryption and seed guard."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from mcias.app import app, get_db
from mcias.models import Base, Organization, User, AuditLog, SessionToken, Permission, Role, UserRole, RolePermission
from mcias.rate_limits import check_limits, cleanup
from mcias.models_operations import RateLimitBucket
from mcias.retention import request_archive, run_archive, scoped_logs
from mcias.backup import decrypt_bundle
from mcias.seed.config import SeedConfig

@pytest.fixture
def database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Organization(id="org-a", name="SYN-A"), Organization(id="org-b", name="SYN-B")]); db.flush()
        db.add_all([User(id="actor", organization_id="org-a", username="SYN-actor", password_hash="not-a-login"),
                    User(id="foreign", organization_id="org-b", username="SYN-foreign", password_hash="not-a-login")]); db.flush()
        db.add(Role(id="role", code="SYN-archive")); db.flush()
        db.add(UserRole(user_id="actor", role_id="role"))
        for code in ["retention.read", "retention.archive"]:
            db.add(Permission(id=code, code=code)); db.flush()
            db.add(RolePermission(role_id="role", permission_id=code))
        db.add(SessionToken(user_id="actor", token_hash=hashlib.sha256(b"session").hexdigest(), expires_at=datetime.now(timezone.utc)+timedelta(hours=1)))
        db.add_all([AuditLog(actor_id="actor", action="synthetic_event", resource_type="test", created_at=datetime(2020,1,2,tzinfo=timezone.utc), details={"message":"اختبار"}),
                    AuditLog(actor_id="foreign", action="foreign-secret", resource_type="test", created_at=datetime(2020,1,2,tzinfo=timezone.utc)),
                    AuditLog(action="system-secret", resource_type="test", created_at=datetime(2020,1,2,tzinfo=timezone.utc))])
        db.commit()
    yield engine
    engine.dispose()

def test_limits_verified_user_cannot_evade_by_token_rotation_and_audit_bounded(database):
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    with Session(database) as db:
        assert check_limits(db, "Bearer session", "127.0.0.1", now=now,user_limit=2,ip_limit=100) is None
        assert check_limits(db, "Bearer session", "127.0.0.2", now=now,user_limit=2,ip_limit=100) is None
        assert check_limits(db, "Bearer session", "127.0.0.3", now=now,user_limit=2,ip_limit=100)==60
        for _ in range(20): assert check_limits(db,"Bearer session","127.0.0.3",now=now,user_limit=2,ip_limit=100)==60
        logs=db.scalars(select(AuditLog).where(AuditLog.action=="api_rate_limit_exceeded")).all()
        assert len(logs)==1 and logs[0].details["scope"]=="user"
        assert check_limits(db,"Bearer session","127.0.0.3",now=now+timedelta(minutes=1),user_limit=2,ip_limit=100) is None
        assert cleanup(db, now+timedelta(days=2)) > 0
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action=="api_rate_limit_exceeded"))==1

def test_invalid_sessions_use_ip_quota(database):
    with Session(database) as db:
        assert check_limits(db,"Bearer fake","127.0.0.1",ip_limit=1) is None
        assert check_limits(db,None,"127.0.0.1",ip_limit=1) is not None

def test_encrypted_archive_is_tenant_only_verified_idempotent_and_append_only(database,tmp_path):
    with Session(database) as db:
        actor=db.get(User,"actor"); job=request_archive(db,actor,"2020-01")
        receipt=run_archive(db,job,tmp_path,b"a"*32)
        assert receipt["row_count"]==1 and receipt["verified"] and not receipt["purged"]
        archive=tmp_path/(job+".mcias")
        assert archive.stat().st_mode & 0o777 == 0o600
        assert b"synthetic_event" not in archive.read_bytes()
        data=json.loads(decrypt_bundle(archive.read_bytes(),b"a"*32)["audit.json"])
        assert len(data["rows"])==1 and data["rows"][0]["action"]=="synthetic_event"
        assert run_archive(db,job,tmp_path,b"a"*32)==receipt
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action=="synthetic_event"))==1
        with pytest.raises(Exception): decrypt_bundle(archive.read_bytes(),b"b"*32)
        with pytest.raises(ValueError): request_archive(db,actor,"2999-01")

def test_retention_api_denies_anonymous_and_returns_queued_status(database):
    def dependency():
        with Session(database) as db: yield db
    app.dependency_overrides[get_db]=dependency
    try:
        with TestClient(app) as c:
            assert c.get("/api/v1/admin/retention/status").status_code==401
            h={"Authorization":"Bearer session"}
            result=c.get("/api/v1/admin/retention/status",headers=h)
            assert result.status_code==200 and not result.json()["purge_enabled"]
            assert c.post("/api/v1/admin/retention/archive",headers=h,json={"month":"2020-01"}).status_code==202
            assert c.post("/api/v1/admin/retention/archive",headers=h,json={"month":"../evil"}).status_code==422
            with Session(database) as db:
                db.execute(__import__("sqlalchemy").delete(RolePermission));db.commit()
            assert c.get("/api/v1/admin/retention/status",headers=h).status_code==403
    finally: app.dependency_overrides.pop(get_db,None)

@pytest.mark.parametrize("url,environment", [("postgresql://localhost/client","development"),("postgresql://localhost/synthetic_e2e","production"),("sqlite://","development")])
def test_seed_refuses_nonisolated_database(url,environment):
    with pytest.raises(ValueError): SeedConfig(url,environment).validate()

def test_seed_reset_wrong_confirmation_never_connects(monkeypatch):
    from mcias.seed.reset import reset
    config=SeedConfig("postgresql://localhost/synthetic_e2e","development")
    with pytest.raises(ValueError): reset(config,"client")

def test_middleware_returns_429_retry_after_and_ignores_forwarded_headers(database, monkeypatch):
    # Freeze only the wall clock: 101 HTTP calls may otherwise cross a fixed
    # minute boundary and correctly consume two different real quota buckets.
    import mcias.rate_limits as limiter
    instant = datetime(2026, 10, 21, 12, 0, 15, tzinfo=timezone.utc)
    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(limiter, "datetime", FixedClock)
    def dependency():
        with Session(database) as db: yield db
    app.dependency_overrides[get_db]=dependency
    try:
        with TestClient(app) as c:
            for i in range(100):
                response=c.get('/api/v1/admin/retention/status',headers={'Authorization':'Bearer session','X-Forwarded-For':str(i)})
                assert response.status_code==200
            response=c.get('/api/v1/admin/retention/status',headers={'Authorization':'Bearer session'})
            assert response.status_code==429
            assert 1 <= int(response.headers['retry-after']) <= 60
            assert response.headers['cache-control']=='no-store'
            assert c.get('/health/live').status_code==200
            with Session(database) as db:
                buckets = db.scalars(select(RateLimitBucket)).all()
                assert len(buckets) == 2  # one real IP bucket and one user bucket
                assert {bucket.requests for bucket in buckets} == {101}
                assert {bucket.window_start for bucket in buckets} == {instant.replace(
                    second=0, microsecond=0, tzinfo=None)}
                assert db.scalar(select(func.count()).select_from(AuditLog).where(
                    AuditLog.action == "api_rate_limit_exceeded")) == 1
    finally: app.dependency_overrides.pop(get_db,None)


def test_real_rate_limit_buckets_explain_minute_boundary_reset(database):
    """Reproduce the old 429 expectation's timing failure from stored rows."""
    instant = datetime(2026, 10, 21, 12, 0, 59, tzinfo=timezone.utc)
    with Session(database) as db:
        for _ in range(100):
            assert check_limits(db, "Bearer session", "testclient", now=instant) is None
        # Request 101 in the next minute is allowed by the actual fixed window.
        assert check_limits(db, "Bearer session", "testclient", now=instant + timedelta(seconds=1)) is None
    with Session(database) as db:
        scope_hash = hashlib.sha256(b"user:actor").hexdigest()
        buckets = db.scalars(select(RateLimitBucket).where(
            RateLimitBucket.scope_hash == scope_hash).order_by(RateLimitBucket.window_start)).all()
        assert [(bucket.window_start, bucket.requests) for bucket in buckets] == [
            (instant.replace(second=0, tzinfo=None), 100),
            ((instant + timedelta(seconds=1)).replace(second=0, tzinfo=None), 1)]


def test_middleware_database_failure_is_closed():
    from mcias.app import get_rate_limit_db
    def unavailable():
        raise RuntimeError('PRIVATE DATABASE DETAILS')
        yield
    app.dependency_overrides[get_rate_limit_db]=unavailable
    try:
        with TestClient(app) as c:
            response=c.get('/api/v1/admin/retention/status')
            assert response.status_code==503 and 'PRIVATE' not in response.text
    finally: app.dependency_overrides.pop(get_rate_limit_db,None)
