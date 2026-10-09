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
    if request.headers.get("content-length") and int(request.headers["content-length"]) > MAX_BYTES:
        raise HTTPException(413, "file too large")
    data = await request.body()
    if not data or len(data) > MAX_BYTES:
        raise HTTPException(413, "file empty or too large")
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
