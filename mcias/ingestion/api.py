"""Authenticated, tenant-isolated ingestion endpoints; bounded upload size."""
import os
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from mcias.auth import resolve_user
from mcias.app import get_db
from mcias.tenant import require_organization
from mcias.storage import EncryptedStore
from mcias.ingestion.file_scanner import MAX_BYTES
from mcias.ingestion.orchestrator import ingest
from mcias.models_ingestion import IngestionDocument, IngestionJob, QuarantineItem

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])

@router.post("/uploads")
async def upload(request: Request, filename: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, _ = resolve_user(db, authorization)
    require_organization(db, user, user.organization_id, "ingestion.upload")
    if len(filename) > 250 or not filename or "/" in filename or chr(92) in filename:
        raise HTTPException(400, "invalid filename")
    length = request.headers.get("content-length")
    if length is not None:
        try:
            declared = int(length)
        except ValueError:
            raise HTTPException(400, "invalid content length")
        if declared < 0 or declared > MAX_BYTES:
            raise HTTPException(413, "file too large")
    chunks = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_BYTES:
            raise HTTPException(413, "file too large")
        chunks.append(chunk)
    if not total:
        raise HTTPException(400, "empty file")
    data = b"".join(chunks)
    try:
        key = bytes.fromhex(os.environ["MCIAS_STORAGE_KEY"])
        store = EncryptedStore(os.environ["MCIAS_STORAGE_DIR"], key)
    except (KeyError, ValueError):
        raise HTTPException(503, "encrypted storage unavailable")
    return ingest(db, store, user.organization_id, user.id, filename, data)

@router.get("/jobs/{job_id}")
def job_status(job_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, _ = resolve_user(db, authorization)
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    require_organization(db, user, job.organization_id, "ingestion.read")
    return {"id": job.id, "status": job.status, "manifest": job.manifest}

@router.get("/documents/{document_id}")
def document_status(document_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, _ = resolve_user(db, authorization)
    document = db.get(IngestionDocument, document_id)
    if document is None:
        raise HTTPException(404, "document not found")
    require_organization(db, user, document.organization_id, "ingestion.read")
    return {"id": document.id, "sha256": document.sha256, "status": document.status}

@router.get("/documents/{document_id}/manifest")
def document_manifest(document_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    from sqlalchemy import select
    user, _ = resolve_user(db, authorization)
    document = db.get(IngestionDocument, document_id)
    if document is None:
        raise HTTPException(404, "document not found")
    require_organization(db, user, document.organization_id, "ingestion.read")
    job = db.scalar(select(IngestionJob).where(IngestionJob.document_id == document.id).order_by(IngestionJob.created_at.desc()))
    return {"document_id": document.id, "manifest": job.manifest if job else {}, "status": job.status if job else document.status}

@router.get("/jobs/{job_id}/quarantine")
def job_quarantine(job_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    from sqlalchemy import select
    user, _ = resolve_user(db, authorization)
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    require_organization(db, user, job.organization_id, "ingestion.read")
    items = db.scalars(select(QuarantineItem).where(QuarantineItem.job_id == job.id)).all()
    return {"job_id": job.id, "items": [{"reason": x.reason, "locator": x.locator} for x in items]}

@router.get("/jobs/{job_id}/records")
def job_records(job_id: str, limit: int = 100, offset: int = 0, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    from sqlalchemy import select
    from mcias.models_ingestion import ExtractedSourceRecord
    user, _ = resolve_user(db, authorization)
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    require_organization(db, user, job.organization_id, "ingestion.read")
    if limit < 1 or limit > 100 or offset < 0:
        raise HTTPException(400, "invalid pagination")
    records = db.scalars(select(ExtractedSourceRecord).where(ExtractedSourceRecord.job_id == job.id).order_by(ExtractedSourceRecord.id).limit(limit).offset(offset)).all()
    return {"job_id": job.id, "records": [{"id": x.id, "locator": x.locator, "values": x.values, "confidence": x.confidence} for x in records]}

@router.post("/jobs/{job_id}/quarantine/{quarantine_id}/review")
async def review_quarantine(job_id: str, quarantine_id: str, request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    from mcias.ingestion.review import decide, ReviewDenied
    user, _ = resolve_user(db, authorization)
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    require_organization(db, user, job.organization_id, "ingestion.review")
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "invalid review")
    try:
        return decide(db, user, job_id, quarantine_id, body.get("decision"), body.get("rationale"))
    except ReviewDenied as exc:
        raise HTTPException(409, str(exc)) from exc
