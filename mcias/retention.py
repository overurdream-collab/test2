"""Local encrypted monthly archive jobs. Never removes immutable audit rows."""
import hashlib
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from mcias.models import AuditLog, User
from mcias.backup import encrypt_bundle, decrypt_bundle

MAX_ROWS = 10000

def month_bounds(month):
    start = date.fromisoformat(month + "-01")
    end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    return datetime.combine(start, datetime.min.time(), timezone.utc), datetime.combine(end, datetime.min.time(), timezone.utc)

def scoped_logs(organization_id):
    # NULL/system actors are deliberately not included in tenant archives.
    return select(AuditLog).join(User, User.id == AuditLog.actor_id).where(User.organization_id == organization_id)

def request_archive(db, actor, month):
    start, end = month_bounds(month)
    if end > datetime.now(timezone.utc):
        raise ValueError("only completed months may be archived")
    job = AuditLog(actor_id=actor.id, action="retention_archive_requested", resource_type="retention",
        resource_id=str(uuid4()), details={"month": month, "organization_id": actor.organization_id})
    db.add(job); db.commit()
    return job.resource_id

def run_archive(db, job_id, directory, key):
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:id, 0))"), {"id": job_id})
    job = db.scalar(select(AuditLog).where(AuditLog.resource_id == job_id,
                                         AuditLog.action == "retention_archive_requested"))
    if job is None:
        raise ValueError("archive request not found")
    existing = db.scalar(select(AuditLog).where(AuditLog.resource_id == job_id,
                                              AuditLog.action == "retention_archive_verified"))
    if existing:
        return existing.details
    actor = db.get(User, job.actor_id)
    if actor is None or not actor.active or actor.organization_id != job.details["organization_id"]:
        raise ValueError("archive tenant mismatch")
    from mcias.auth import require_permission
    require_permission(db, actor, "retention.archive")
    start, end = month_bounds(job.details["month"])
    rows = db.scalars(scoped_logs(actor.organization_id).where(
        AuditLog.created_at >= start, AuditLog.created_at < end).order_by(
        AuditLog.created_at, AuditLog.id).limit(MAX_ROWS + 1)).all()
    if len(rows) > MAX_ROWS:
        raise ValueError("archive exceeds bounded worker size; split/streaming worker required")
    data = [{"id": r.id, "actor_id": r.actor_id, "action": r.action,
             "resource_type": r.resource_type, "resource_id": r.resource_id,
             "details": r.details, "created_at": r.created_at.isoformat()} for r in rows]
    payload = json.dumps({"format": "mcias-audit-archive-v1", "organization_id": actor.organization_id,
                          "month": job.details["month"], "rows": data},
                         ensure_ascii=False, sort_keys=True).encode("utf-8")
    encrypted = encrypt_bundle({"audit.json": payload}, key)
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if folder.is_symlink():
        raise ValueError("archive directory must not be a symlink")
    path = folder / (job_id + ".mcias")
    # Atomic publication with private permissions; recovery can safely retry a job.
    temporary = folder / (job_id + "." + uuid4().hex + ".tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(encrypted); output.flush(); os.fsync(output.fileno())
        if decrypt_bundle(temporary.read_bytes(), key)["audit.json"] != payload:
            raise ValueError("archive readback verification failed")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    receipt = {"month": job.details["month"], "row_count": len(rows),
               "sha256": hashlib.sha256(encrypted).hexdigest(), "verified": True,
               "purged": False}
    db.add(AuditLog(actor_id=actor.id, action="retention_archive_verified",
                   resource_type="retention", resource_id=job_id, details=receipt))
    db.commit()
    return receipt
