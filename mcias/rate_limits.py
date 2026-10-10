"""Atomic shared PostgreSQL fixed-minute limits, bounded operational audit logging.

Forwarded headers are deliberately ignored. The deployment proxy must normalize
ASGI client addresses and trust only its own immediate proxy, never '*'.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import delete
from mcias.auth import resolve_user
from mcias.models import AuditLog
from mcias.models_operations import RateLimitBucket

EXEMPT = frozenset({"/api/v1/auth/login", "/api/v1/auth/logout", "/api/v1/workspace/demo-availability", "/api/v1/system/status"})

def consume(db, scope, now):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    key = hashlib.sha256(scope.encode()).hexdigest()
    stmt = insert(RateLimitBucket).values(scope_hash=key, window_start=now, requests=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=["scope_hash", "window_start"],
        set_={"requests": RateLimitBucket.requests + 1}).returning(RateLimitBucket.requests)
    return db.scalar(stmt)

def check_limits(db, authorization, client_ip, *, now=None, user_limit=100, ip_limit=1000):
    instant = now or datetime.now(timezone.utc)
    window = instant.replace(second=0, microsecond=0)
    actor = None
    if authorization:
        try:
            actor, _ = resolve_user(db, authorization)
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
    scopes = [("ip:" + client_ip, ip_limit, "ip")]
    if actor:
        scopes.append(("user:" + actor.id, user_limit, "user"))
    exceeded = False
    for scope, limit, kind in scopes:
        count = consume(db, scope, window)
        if count > limit:
            exceeded = True
            if count == limit + 1:
                # One event per exceeded bucket/minute; no token, raw IP or path.
                db.add(AuditLog(actor_id=actor.id if actor else None,
                    action="api_rate_limit_exceeded", resource_type="api",
                    details={"scope": kind, "limit": limit, "window_seconds": 60}))
    db.commit()
    return max(1, 60 - instant.second) if exceeded else None

def cleanup(db, now=None):
    """Run from a maintenance job, never delete audit history."""
    now = now or datetime.now(timezone.utc)
    count = db.execute(delete(RateLimitBucket).where(
        RateLimitBucket.window_start < now - timedelta(hours=24))).rowcount
    db.commit()
    return count

async def rate_limit_middleware(request, call_next):
    if not request.url.path.startswith("/api/") or request.url.path in EXEMPT:
        return await call_next(request)
    from mcias.app import app, get_db, get_settings, get_rate_limit_db
    from starlette.routing import Match
    if not any(route.matches(request.scope)[0] == Match.FULL for route in app.routes):
        return await call_next(request)
    from fastapi.responses import JSONResponse
    from starlette.concurrency import run_in_threadpool
    def check():
        provider = app.dependency_overrides.get(get_rate_limit_db) or app.dependency_overrides.get(get_db)
        generator = provider() if provider else get_db(get_settings())
        try:
            db = next(generator)
            return check_limits(db, request.headers.get("authorization"),
                                request.client.host if request.client else "unknown")
        finally:
            generator.close()
    try:
        retry = await run_in_threadpool(check)
    except Exception:
        # Failure cannot silently disable a security control; no DB details leak.
        return JSONResponse({"detail": "request limiter unavailable"}, status_code=503,
                            headers={"Cache-Control": "no-store"})
    if retry:
        return JSONResponse({"detail": "request rate exceeded"}, status_code=429,
                            headers={"Retry-After": str(retry), "Cache-Control": "no-store"})
    return await call_next(request)
