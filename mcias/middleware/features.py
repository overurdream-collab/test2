"""Optional legacy-API rollout guard; enabled by default in production.

New feature/registry APIs always enforce their own guards, including development.
This middleware never replaces the existing RBAC or financial authorization.
"""
import os
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from mcias.api.dependencies import open_db
from mcias.auth import resolve_user
from mcias.services.feature_service import check_feature, is_super_admin
from mcias.services.rbac_service import _live_user
from datetime import date

def required_feature(path):
    pairs = (
        ("/api/v1/claims/batches", "claims.batches"), ("/api/v1/claims/entries", "claims.list"),
        ("/api/v1/audits/", "audit.snapshots"), ("/api/v1/audit-policies/", "inputs.approvals"),
        ("/api/v1/governance/", "governance.cases"), ("/api/v1/reports/", "reports.list"),
        ("/api/v1/report-explorer/", "reports.list"), ("/api/v1/intelligence/", "intelligence.analysis"),
        ("/api/v1/reference/contracts", "inputs.contracts"), ("/api/v1/reference/categories", "beneficiaries.categories"),
        ("/api/v1/reference/enrollments", "beneficiaries.names"), ("/api/v1/reference/eligibility/", "beneficiaries.names"),
    )
    for prefix, code in pairs:
        if path.startswith(prefix): return code
    if path.startswith("/api/v1/workspace/catalog/"):
        kind = path.rsplit("/", 1)[-1]
        return {"claims":"claims.list", "batches":"claims.batches", "contracts":"inputs.contracts",
            "audits":"audit.snapshots", "cases":"governance.cases", "users":"users.list"}.get(kind)
    if path.startswith("/api/v1/workspace/claims/"): return "claims.list"
    return None

async def feature_middleware(request, call_next):
    enabled = os.getenv("MCIAS_FEATURE_ENFORCEMENT", "true" if os.getenv("MCIAS_ENVIRONMENT") == "production" else "false") == "true"
    code = required_feature(request.url.path)
    if not enabled or not code: return await call_next(request)
    def probe():
        provider = open_db()
        try:
            db = next(provider)
            actor, _ = resolve_user(db, request.headers.get("authorization"))
            if not _live_user(actor, date.today()):
                raise HTTPException(401, "invalid session")
            if not is_super_admin(db, actor) and not check_feature(db, actor.organization_id, code):
                raise HTTPException(403, "organization feature is not enabled")
        finally: provider.close()
    try: await run_in_threadpool(probe)
    except HTTPException as exc:
        return JSONResponse({"detail":exc.detail}, status_code=exc.status_code, headers={"Cache-Control":"no-store"})
    except Exception:
        return JSONResponse({"detail":"feature verification unavailable"}, status_code=503, headers={"Cache-Control":"no-store"})
    return await call_next(request)
