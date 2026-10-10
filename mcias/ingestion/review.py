"""Human quarantine decisions with explicit tenant authority and immutable audit."""
from datetime import datetime, timezone
from sqlalchemy import select
from mcias.models import AuditLog
from mcias.models_ingestion import IngestionJob, QuarantineItem

class ReviewDenied(ValueError):
    pass

def decide(db, actor, job_id: str, quarantine_id: str, decision: str, rationale: str):
    if decision not in ("reject", "request_reupload", "acknowledge") or not isinstance(rationale, str) or len(rationale.strip()) < 10:
        raise ReviewDenied("valid decision and rationale required")
    job = db.scalar(select(IngestionJob).where(IngestionJob.id == job_id).with_for_update())
    if job is None or job.organization_id != actor.organization_id:
        raise ReviewDenied("review not permitted")
    item = db.scalar(select(QuarantineItem).where(QuarantineItem.id == quarantine_id, QuarantineItem.job_id == job.id).with_for_update())
    if item is None:
        raise ReviewDenied("quarantine item not found")
    if db.scalar(select(AuditLog.id).where(AuditLog.action == "ingestion_quarantine_reviewed", AuditLog.resource_id == item.id)):
        raise ReviewDenied("already reviewed")
    db.add(AuditLog(actor_id=actor.id, action="ingestion_quarantine_reviewed", resource_type="ingestion_quarantine", resource_id=item.id,
                    details={"decision": decision, "rationale": rationale.strip(), "job_id": job.id, "original_reason": item.reason}))
    db.commit()
    return {"id": item.id, "decision": decision, "job_status": job.status}
