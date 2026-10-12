"""Metadata-only HTTP audit, separate from transactional service change events."""
import logging
from uuid import uuid4
from starlette.concurrency import run_in_threadpool
from mcias.api.dependencies import open_db
from mcias.models import AuditLog

logger = logging.getLogger(__name__)

def record_request(scope, status, request_id):
    actor = scope.get("state", {}).get("rbac_actor", {})
    route = scope.get("route")
    # Unmatched paths and query strings may contain medical data or credentials.
    endpoint = getattr(route, "path", None)
    method = scope["method"]
    result = "denied" if status in (401, 403) else "failure" if status >= 400 else "success"
    provider = open_db()
    try:
        db = next(provider)
        if not actor:
            from datetime import date
            from fastapi import HTTPException
            from mcias.auth import resolve_user
            from mcias.services.rbac_service import _live_user
            authorization = next((value.decode("latin-1") for name, value in scope.get("headers", [])
                                  if name.lower() == b"authorization"), None)
            try:
                user, session = resolve_user(db, authorization)
                if _live_user(user, date.today()):
                    actor = {"id": user.id, "username": user.username,
                             "organization_id": user.organization_id, "session_id": session.id}
            except HTTPException:
                pass
        db.add(AuditLog(actor_id=actor.get("id"), organization_id=actor.get("organization_id"),
            actor_username=actor.get("username"), session_id=actor.get("session_id"),
            action="http.request", resource_type="http_endpoint",
            category="http_access", severity="error" if status >= 500 else "warning" if status >= 400 else "info",
            endpoint=endpoint, method=method, result=result, request_id=request_id,
            error_code=f"HTTP_{status}" if status >= 400 else None,
            details={"status_code": status}))
        db.commit()
    except Exception:
        # Business mutations already commit their own audit atomically. A failure
        # in this auxiliary access event must not turn a committed success into 500.
        logger.error("HTTP audit persistence unavailable; request_id=%s", request_id)
    finally:
        provider.close()

class AuditMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = str(uuid4())
        status = 500

        async def audited_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, audited_send)
        finally:
            if scope["method"] in ("POST", "PUT", "PATCH", "DELETE") or status >= 400:
                await run_in_threadpool(record_request, scope, status, request_id)
