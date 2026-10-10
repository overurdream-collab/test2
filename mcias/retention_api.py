"""Permission and tenant guarded archival requests; no purge endpoint."""
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user, require_permission
from mcias.models import AuditLog
from mcias.retention import request_archive, scoped_logs
router = APIRouter(prefix="/api/v1/admin/retention", tags=["retention"])

class ArchiveRequest(BaseModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")

def guard(db, authorization, permission):
    actor, _ = resolve_user(db, authorization)
    require_permission(db, actor, permission)
    if not actor.organization_id:
        raise HTTPException(403, "organization scope required")
    return actor

@router.get("/status")
def status(response: Response, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    actor = guard(db, authorization, "retention.read")
    response.headers["Cache-Control"] = "no-store"
    base = scoped_logs(actor.organization_id).subquery()
    count = db.scalar(select(func.count()).select_from(base))
    completed = db.scalar(select(func.count()).select_from(base).where(base.c.action == "retention_archive_verified"))
    requested = db.scalar(select(func.count()).select_from(base).where(base.c.action == "retention_archive_requested"))
    return {"organization_id": actor.organization_id, "audit_rows": count,
            "archive_requested": requested, "archive_verified": completed,
            "proposed_retention_years": 7, "policy_status": "pending_institutional_approval",
            "purge_enabled": False, "storage": "local_encrypted_monthly_files",
            "system_actor_rows_included": False}

@router.post("/archive", status_code=202)
def archive(payload: ArchiveRequest, response: Response, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    actor = guard(db, authorization, "retention.archive")
    response.headers["Cache-Control"] = "no-store"
    try:
        job_id = request_archive(db, actor, payload.month)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"job_id": job_id, "status": "queued", "purge_enabled": False}
