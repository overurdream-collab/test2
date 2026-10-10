"""Transactional ingestion: encrypted original first, tenant-scoped deduplication, reviewable extraction."""
from sqlalchemy import select
from mcias.models import SourceFile, AuditLog
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord, QuarantineItem
from mcias.ingestion.fingerprint import sha256
from mcias.ingestion.file_scanner import identify
from mcias.ingestion.isolated_parser import isolated_parse
from mcias.ingestion.manifest import manifest
from mcias.ingestion.provenance import locator_dict
from mcias.ingestion.palermo.palermo_1 import review

class IngestionError(ValueError):
    pass

def ingest(db, store, organization_id: str, actor_id: str, filename: str, data: bytes):
    if not organization_id:
        raise IngestionError("organization required")
    digest = sha256(data)
    previous = db.scalar(select(IngestionDocument).where(IngestionDocument.organization_id == organization_id, IngestionDocument.sha256 == digest))
    if previous:
        return {"document_id": previous.id, "status": "duplicate", "sha256": digest}
    object_id, stored_digest = store.put(data)
    source = SourceFile(sha256=stored_digest, original_filename=filename, storage_key=object_id)
    db.add(source)
    db.flush()
    document = IngestionDocument(organization_id=organization_id, source_id=source.id, sha256=digest, filename=filename, status="processing")
    db.add(document)
    db.flush()
    job = IngestionJob(organization_id=organization_id, document_id=document.id, status="processing", manifest={})
    db.add(job)
    db.flush()
    try:
        extraction = isolated_parse(identify(data, filename), data)
        result = review(extraction)
        for record in extraction.records:
            db.add(ExtractedSourceRecord(job_id=job.id, locator=locator_dict(record.locator), values=record.values, confidence=round(record.confidence*100)))
        for issue in extraction.quarantined:
            db.add(QuarantineItem(job_id=job.id, reason=issue["reason"], locator=issue["locator"]))
        job.manifest = manifest(extraction)
        job.status = result["status"]
    except Exception as exc:
        # Preserve the encrypted original even when parser rejects it.
        job.status = "review_required"
        job.manifest = {"complete": False, "error": type(exc).__name__}
        db.add(QuarantineItem(job_id=job.id, reason="unreadable or unsafe source", locator={"kind":"file","index":1}))
    document.status = job.status
    db.add(AuditLog(actor_id=actor_id, action="source_ingested", resource_type="ingestion_document", resource_id=document.id, details={"sha256": digest, "status": job.status}))
    db.commit()
    return {"document_id": document.id, "job_id": job.id, "status": job.status, "sha256": digest, "manifest": job.manifest}
