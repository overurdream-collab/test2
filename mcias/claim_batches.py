"""G4 batch import with explicit staging, row-level rejection, and idempotent resume."""
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from mcias.models import AuditLog
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord, QuarantineItem
from mcias.models_claims import ClaimBatch, ClaimEntry, ClaimAttachment
from mcias.claim_normalization import normalize, ClaimValidationError

class BatchConflict(ValueError):
    pass

def _document(db,org,document_id):
    document=db.get(IngestionDocument,document_id)
    if document is None or document.organization_id!=org:
        raise BatchConflict("source document not accessible")
    return document

def _job(db,org,document_id):
    jobs=db.scalars(select(IngestionJob).where(IngestionJob.organization_id==org,
        IngestionJob.document_id==document_id).order_by(IngestionJob.created_at.desc())).all()
    if not jobs:
        raise BatchConflict("no extraction job")
    return jobs[0]

def stage(db,actor,document_id):
    if not actor.active or not actor.organization_id:
        raise BatchConflict("active organization required")
    doc=_document(db,actor.organization_id,document_id)
    job=_job(db,actor.organization_id,document_id)
    if doc.status!="extracted" or job.status!="extracted" or not job.manifest.get("complete"):
        raise BatchConflict("source extraction incomplete or quarantined")
    if db.scalar(select(QuarantineItem.id).where(QuarantineItem.job_id==job.id)):
        raise BatchConflict("source has quarantine items")
    existing=db.scalar(select(ClaimBatch).where(ClaimBatch.organization_id==actor.organization_id,
                                                ClaimBatch.ingestion_document_id==doc.id))
    if existing:
        return existing
    count=db.scalar(select(func.count()).select_from(ExtractedSourceRecord).where(
        ExtractedSourceRecord.job_id==job.id))
    if not count:
        raise BatchConflict("source has no extracted records")
    batch=ClaimBatch(organization_id=actor.organization_id,ingestion_document_id=doc.id,
        created_by=actor.id,source_sha256=doc.sha256,record_count=count,imported_count=0,status="staged")
    db.add(batch);db.flush()
    db.add(AuditLog(actor_id=actor.id,action="claim_batch_staged",resource_type="claim_batch",
        resource_id=batch.id,details={"document_id":doc.id,"sha256":doc.sha256,"records":count}))
    db.commit()
    return batch

def preview(db,actor,batch_id,limit=100,offset=0):
    batch=db.get(ClaimBatch,batch_id)
    if batch is None or batch.organization_id!=actor.organization_id:
        raise BatchConflict("batch not accessible")
    job=_job(db,actor.organization_id,batch.ingestion_document_id)
    records=db.scalars(select(ExtractedSourceRecord).where(ExtractedSourceRecord.job_id==job.id)
        .order_by(ExtractedSourceRecord.id).offset(offset).limit(limit)).all()
    results=[]
    for record in records:
        try:
            normalized=normalize(record.values)
            results.append({"record_id":record.id,"locator":record.locator,"valid":True,
                            "claim_reference":normalized["claim_reference"]})
        except ClaimValidationError as exc:
            results.append({"record_id":record.id,"locator":record.locator,"valid":False,"reason":str(exc)})
    return {"batch_id":batch.id,"record_count":batch.record_count,"rows":results}

def resume(db,actor,batch_id,chunk_size=100):
    if not actor.active or not actor.organization_id:
        raise BatchConflict("active organization required")
    batch=db.scalar(select(ClaimBatch).where(ClaimBatch.id==batch_id, ClaimBatch.organization_id==actor.organization_id).with_for_update())
    if batch is None or batch.organization_id!=actor.organization_id:
        raise BatchConflict("batch not accessible")
    if batch.status=="imported":
        return {"batch_id":batch.id,"status":batch.status,"imported_count":batch.imported_count}
    if batch.status not in ("staged","importing","review_required"):
        raise BatchConflict("invalid batch state")
    doc=_document(db,actor.organization_id,batch.ingestion_document_id)
    if doc.sha256!=batch.source_sha256 or doc.status!="extracted":
        raise BatchConflict("source changed or incomplete")
    job=_job(db,actor.organization_id,doc.id)
    if job.status!="extracted" or not job.manifest.get("complete"):
        raise BatchConflict("extraction not complete")
    if db.scalar(select(QuarantineItem.id).where(QuarantineItem.job_id==job.id)):
        raise BatchConflict("source has quarantine")
    records=db.scalars(select(ExtractedSourceRecord).where(ExtractedSourceRecord.job_id==job.id)
        .order_by(ExtractedSourceRecord.id)).all()
    if len(records)!=batch.record_count:
        raise BatchConflict("source record count changed")
    already=set(db.scalars(select(ClaimEntry.extracted_record_id).where(ClaimEntry.batch_id==batch.id)).all())
    if chunk_size<=0 or chunk_size>1000:
        raise BatchConflict("invalid chunk size")
    accepted=0
    rejected=[]
    for record in records:
        if record.id in already:
            continue
        try:
            values=normalize(record.values)
        except ClaimValidationError as exc:
            rejected.append({"record_id":record.id,"locator":record.locator,"reason":str(exc)})
            continue
        if accepted>=chunk_size:
            break
        accepted+=1
        db.add(ClaimEntry(organization_id=actor.organization_id,batch_id=batch.id,
            extracted_record_id=record.id,source_locator=record.locator,source_values=record.values,**values))
        batch.imported_count+=1
    db.flush()
    batch.imported_count=db.scalar(select(func.count()).select_from(ClaimEntry).where(ClaimEntry.batch_id==batch.id))
    batch.status="review_required" if rejected else ("imported" if batch.imported_count==batch.record_count else "importing")
    db.add(AuditLog(actor_id=actor.id,action="claim_batch_resumed",resource_type="claim_batch",
        resource_id=batch.id,details={"imported":batch.imported_count,"rejected_count":len(rejected),
                                       "status":batch.status}))
    db.commit()
    return {"batch_id":batch.id,"status":batch.status,"imported_count":batch.imported_count,
            "record_count":batch.record_count,"rejected":rejected}

def attach(db,actor,claim_id,document_id):
    claim=db.get(ClaimEntry,claim_id)
    if claim is None or claim.organization_id!=actor.organization_id:
        raise BatchConflict("claim not accessible")
    doc=_document(db,actor.organization_id,document_id)
    if doc.status not in ("extracted","review_required"):
        raise BatchConflict("attachment source is not processed")
    existing=db.scalar(select(ClaimAttachment).where(ClaimAttachment.claim_id==claim.id,
        ClaimAttachment.ingestion_document_id==doc.id))
    if existing:
        return existing
    link=ClaimAttachment(organization_id=actor.organization_id,claim_id=claim.id,
        ingestion_document_id=doc.id,document_sha256=doc.sha256,linked_by=actor.id)
    db.add(link);db.flush()
    db.add(AuditLog(actor_id=actor.id,action="claim_attachment_linked",resource_type="claim_attachment",
        resource_id=link.id,details={"claim_id":claim.id,"document_id":doc.id,"sha256":doc.sha256}))
    db.commit()
    return link
