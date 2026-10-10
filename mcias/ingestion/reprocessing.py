"""Reprocess the same encrypted original as a new job, preserving previous evidence."""
from sqlalchemy import select
from mcias.models import SourceFile, AuditLog
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord, QuarantineItem
from mcias.ingestion.file_scanner import identify
from mcias.ingestion.malware_scan import scan
from mcias.ingestion.isolated_parser import isolated_parse
from mcias.ingestion.manifest import manifest
from mcias.ingestion.provenance import locator_dict
from mcias.ingestion.palermo.palermo_1 import review

def retry(db, store, document_id: str, actor):
    document = db.scalar(select(IngestionDocument).where(IngestionDocument.id == document_id).with_for_update())
    if document is None or document.organization_id != actor.organization_id:
        raise ValueError("document unavailable")
    source = db.get(SourceFile, document.source_id)
    if source is None:
        raise ValueError("source missing")
    original = store.get(source.storage_key, source.sha256)
    job = IngestionJob(organization_id=document.organization_id, document_id=document.id, status="processing", manifest={})
    db.add(job)
    db.flush()
    try:
        scan(original)
        result = isolated_parse(identify(original, document.filename), original)
        decision = review(result)
        for record in result.records:
            db.add(ExtractedSourceRecord(job_id=job.id, locator=locator_dict(record.locator), values=record.values, confidence=round(record.confidence * 100)))
        for finding in result.quarantined:
            db.add(QuarantineItem(job_id=job.id, reason=finding["reason"], locator=finding["locator"]))
        job.manifest = manifest(result)
        job.status = decision["status"]
    except Exception as exc:
        job.status = "review_required"
        job.manifest = {"complete": False, "error": type(exc).__name__, "expected_units": 1, "processed_units": 0, "quarantined_units": 1}
        db.add(QuarantineItem(job_id=job.id, reason="reprocessing failed", locator={"kind": "file", "index": 1}))
    document.status = job.status
    db.add(AuditLog(actor_id=actor.id, action="ingestion_reprocessed", resource_type="ingestion_document", resource_id=document.id,
                    details={"job_id": job.id, "sha256": document.sha256, "status": job.status}))
    db.commit()
    return {"document_id": document.id, "job_id": job.id, "status": job.status, "manifest": job.manifest}
