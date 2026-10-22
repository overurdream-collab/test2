"""G4 batch import with explicit staging, row-level rejection, and idempotent resume."""
import hashlib
import json
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from mcias.models import AuditLog, User, SourceFile
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord, QuarantineItem
from mcias.models_claims import ClaimBatch, ClaimEntry, ClaimAttachment
from mcias.claim_normalization import normalize, ClaimValidationError, FIELDS
from mcias.policy import has_permission

SOURCE_MAPPING_VERSION = "g4-canonical-v1"
SOURCE_SCOPE_ACTION = "claim_source_scope_approved"
SHEET_TYPES = frozenset(("CLAIMS", "PAYMENT", "FAMILY_SUMMARY", "OTHER"))

class BatchConflict(ValueError):
    pass

def _document(db,org,document_id):
    document=db.get(IngestionDocument,document_id)
    if document is None or document.organization_id!=org:
        raise BatchConflict("source document not accessible")
    source = db.get(SourceFile, document.source_id)
    if source is None or source.sha256 != document.sha256:
        raise BatchConflict("original source hash conflict")
    return document

def _job(db,org,document_id):
    jobs=db.scalars(select(IngestionJob).where(IngestionJob.organization_id==org,
        IngestionJob.document_id==document_id).order_by(IngestionJob.created_at.desc())).all()
    if not jobs:
        raise BatchConflict("no extraction job")
    return jobs[0]

def _records(db, job):
    return db.scalars(select(ExtractedSourceRecord).where(
        ExtractedSourceRecord.job_id == job.id).order_by(ExtractedSourceRecord.id)).all()

def _complete(db, doc, job):
    if doc.status != "extracted" or job.status != "extracted" or not job.manifest.get("complete"):
        raise BatchConflict("source extraction incomplete or quarantined")
    if db.scalar(select(QuarantineItem.id).where(QuarantineItem.job_id == job.id)):
        raise BatchConflict("source has quarantine items")

def _xlsx(doc, job, records):
    return (doc.filename.lower().endswith(".xlsx") or job.manifest.get("format") == "xlsx"
            or any(r.locator.get("kind") == "sheet" for r in records))

def _source_fingerprint(doc, job, records):
    inventory = job.manifest.get("worksheet_inventory")
    if not isinstance(inventory, list) or not inventory:
        raise BatchConflict("trusted worksheet inventory required")
    sheets = {}
    for sheet in inventory:
        if (not isinstance(sheet, dict) or type(sheet.get("index")) is not int
            or sheet["index"] < 1 or sheet["index"] in sheets
            or not isinstance(sheet.get("name"), str) or not sheet["name"]
            or not isinstance(sheet.get("headers"), list)
            or type(sheet.get("data_rows")) is not int or sheet["data_rows"] < 0):
            raise BatchConflict("invalid worksheet inventory")
        sheets[sheet["index"]] = sheet
    counts = {index: 0 for index in sheets}
    positions = set()
    for record in records:
        loc = record.locator
        index, row = loc.get("index"), loc.get("row")
        if (loc.get("kind") != "sheet" or type(index) is not int or index not in sheets
            or type(row) is not int or row < 2 or (index, row) in positions
            or loc.get("sheet_name") != sheets[index]["name"]):
            raise BatchConflict("source worksheet locator conflict")
        positions.add((index, row))
        counts[index] += 1
    if any(counts[index] != sheet["data_rows"] for index, sheet in sheets.items()):
        raise BatchConflict("source worksheet accounting mismatch")
    payload = {"document_id": doc.id, "source_id": doc.source_id,
               "source_sha256": doc.sha256, "job_id": job.id,
               "manifest": job.manifest,
               "records": [{"id": r.id, "locator": r.locator, "values": r.values,
                            "confidence": r.confidence} for r in records]}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False).encode()).hexdigest()
    return digest, sheets

def sheet_inventory(db, actor, document_id):
    """Read-only, integrity-checked sheet choices; no source values or PHI."""
    if not actor.active or not actor.organization_id:
        raise BatchConflict("active organization required")
    doc = _document(db, actor.organization_id, document_id)
    job = _job(db, actor.organization_id, doc.id)
    _complete(db, doc, job)
    records = _records(db, job)
    if not _xlsx(doc, job, records):
        raise BatchConflict("Excel worksheet inventory only")
    fingerprint, inventory = _source_fingerprint(doc, job, records)
    return {"document_id": doc.id, "source_sha256": doc.sha256,
            "source_fingerprint": fingerprint,
            "sheets": [
                {"index": index, "name": sheet["name"], "data_rows": sheet["data_rows"],
                 "claims_columns_present": set(FIELDS).issubset(sheet["headers"]),
                 "reserved_non_claims": sheet["name"].strip().upper() in ("PAYMENT", "FAMILY_SUMMARY")}
                for index, sheet in sorted(inventory.items())
            ]}


def approve_source_scope(db, actor, document_id, sheet_types):
    """Approve an observed XLSX inventory; caller flags never authorize import.

    The append-only event binds exact source bytes, extraction, physical rows and
    the identity column mapping. Values and worksheet names stay out of the log.
    """
    current_actor = db.get(User, actor.id)
    if (current_actor is None or not current_actor.active or not current_actor.organization_id
        or not has_permission(db, current_actor, "claims.import")):
        raise BatchConflict("claims.import permission required for source scope approval")
    doc = _document(db, current_actor.organization_id, document_id)
    job = db.scalar(select(IngestionJob).where(IngestionJob.id == _job(
        db, current_actor.organization_id, doc.id).id).with_for_update())
    _complete(db, doc, job)
    records = _records(db, job)
    fingerprint, inventory = _source_fingerprint(doc, job, records)
    if (not isinstance(sheet_types, dict) or any(type(k) is not int for k in sheet_types)
        or set(sheet_types) != set(inventory) or any(v not in SHEET_TYPES for v in sheet_types.values())
        or "CLAIMS" not in sheet_types.values()):
        raise BatchConflict("complete explicit worksheet classification required")
    for index, kind in sheet_types.items():
        if kind == "CLAIMS" and not set(FIELDS).issubset(inventory[index]["headers"]):
            raise BatchConflict("claim worksheet does not satisfy canonical column mapping")
        # These reserved labels cannot be reclassified as claims, even by a reviewer.
        if inventory[index]["name"].strip().upper() in ("PAYMENT", "FAMILY_SUMMARY") and kind == "CLAIMS":
            raise BatchConflict("non-claim worksheet cannot be classified as CLAIMS")
    details = {"organization_id": current_actor.organization_id, "job_id": job.id,
               "source_sha256": doc.sha256, "source_fingerprint": fingerprint,
               "mapping_version": SOURCE_MAPPING_VERSION,
               "sheet_types": {str(k): v for k, v in sorted(sheet_types.items())}}
    previous = db.scalars(select(AuditLog).where(AuditLog.action == SOURCE_SCOPE_ACTION,
        AuditLog.resource_type == "ingestion_document", AuditLog.resource_id == doc.id)).all()
    for event in previous:
        if event.details.get("job_id") == job.id:
            if event.details == details:
                return event
            raise BatchConflict("approved source scope is immutable; reprocess a new extraction")
    if db.scalar(select(ClaimBatch.id).where(ClaimBatch.organization_id == current_actor.organization_id,
        ClaimBatch.ingestion_document_id == doc.id)):
        raise BatchConflict("cannot approve a different scope after staging")
    approval = AuditLog(actor_id=current_actor.id, action=SOURCE_SCOPE_ACTION,
        resource_type="ingestion_document", resource_id=doc.id, details=details)
    db.add(approval)
    db.commit()
    return approval

def _eligible(db, org, doc, job, records):
    if not _xlsx(doc, job, records):
        return records, [], None
    fingerprint, inventory = _source_fingerprint(doc, job, records)
    approvals = db.scalars(select(AuditLog).where(AuditLog.action == SOURCE_SCOPE_ACTION,
        AuditLog.resource_type == "ingestion_document", AuditLog.resource_id == doc.id)).all()
    for approval in approvals:
        evidence = approval.details
        types = evidence.get("sheet_types", {})
        if (evidence.get("organization_id") == org and evidence.get("job_id") == job.id
            and evidence.get("source_sha256") == doc.sha256
            and evidence.get("source_fingerprint") == fingerprint
            and evidence.get("mapping_version") == SOURCE_MAPPING_VERSION
            and isinstance(types, dict) and set(types) == {str(i) for i in inventory}
            and all(kind in SHEET_TYPES for kind in types.values())):
            included = [r for r in records if types[str(r.locator["index"])] == "CLAIMS"]
            excluded = [r for r in records if types[str(r.locator["index"])] != "CLAIMS"]
            return included, excluded, approval
    raise BatchConflict("approved source scope missing or changed")

def _batch_source(db, batch, job, approval):
    if approval is None:
        return
    staged = db.scalar(select(AuditLog).where(AuditLog.action == "claim_batch_staged",
        AuditLog.resource_type == "claim_batch", AuditLog.resource_id == batch.id))
    if (staged is None or staged.details.get("job_id") != job.id
        or staged.details.get("source_scope_approval_id") != approval.id):
        raise BatchConflict("batch source approval changed")

def source_scope(db, actor, document_id):
    """Return verified source lineage for G5 without disclosing raw source values."""
    if not actor.active or not actor.organization_id:
        raise BatchConflict("active organization required")
    doc = _document(db, actor.organization_id, document_id)
    job = _job(db, actor.organization_id, doc.id)
    _complete(db, doc, job)
    records = _records(db, job)
    included, excluded, approval = _eligible(db, actor.organization_id, doc, job, records)
    return {"approval_id": approval.id if approval else None,
            "mapping_version": SOURCE_MAPPING_VERSION if approval else None,
            "source_sha256": doc.sha256, "job_id": job.id,
            "eligible_record_ids": [r.id for r in included],
            "excluded_record_ids": [r.id for r in excluded],
            "source_records": len(records), "eligible_records": len(included),
            "excluded_records": len(excluded)}

def stage(db,actor,document_id):
    if not actor.active or not actor.organization_id:
        raise BatchConflict("active organization required")
    doc=_document(db,actor.organization_id,document_id)
    job=_job(db,actor.organization_id,document_id)
    _complete(db, doc, job)
    records, excluded, approval = _eligible(db, actor.organization_id, doc, job, _records(db, job))
    existing=db.scalar(select(ClaimBatch).where(ClaimBatch.organization_id==actor.organization_id,
                                                ClaimBatch.ingestion_document_id==doc.id))
    if existing:
        _batch_source(db, existing, job, approval)
        return existing
    count=len(records)
    if not count:
        raise BatchConflict("source has no extracted records")
    batch=ClaimBatch(organization_id=actor.organization_id,ingestion_document_id=doc.id,
        created_by=actor.id,source_sha256=doc.sha256,record_count=count,imported_count=0,status="staged")
    db.add(batch);db.flush()
    db.add(AuditLog(actor_id=actor.id,action="claim_batch_staged",resource_type="claim_batch",
        resource_id=batch.id,details={"document_id":doc.id,"sha256":doc.sha256,"records":count,
        "excluded_records":len(excluded),"job_id":job.id,
        "source_scope_approval_id":approval.id if approval else None}))
    db.commit()
    return batch

def preview(db,actor,batch_id,limit=100,offset=0):
    if not actor.active or not actor.organization_id:
        raise BatchConflict("active organization required")
    batch=db.get(ClaimBatch,batch_id)
    if batch is None or batch.organization_id!=actor.organization_id:
        raise BatchConflict("batch not accessible")
    doc=_document(db,actor.organization_id,batch.ingestion_document_id)
    job=_job(db,actor.organization_id,batch.ingestion_document_id)
    _complete(db, doc, job)
    records, excluded, approval = _eligible(db, actor.organization_id, doc, job, _records(db, job))
    _batch_source(db, batch, job, approval)
    if doc.sha256 != batch.source_sha256 or len(records) != batch.record_count:
        raise BatchConflict("source changed or incomplete")
    records=records[offset:offset+limit]
    results=[]
    for record in records:
        try:
            normalized=normalize(record.values)
            results.append({"record_id":record.id,"locator":record.locator,"valid":True,
                            "claim_reference":normalized["claim_reference"]})
        except ClaimValidationError as exc:
            results.append({"record_id":record.id,"locator":record.locator,"valid":False,"reason":str(exc)})
    return {"batch_id":batch.id,"record_count":batch.record_count,"excluded_count":len(excluded),
            "source_scope_approval_id":approval.id if approval else None,"rows":results}

def resume(db,actor,batch_id,chunk_size=100):
    if not actor.active or not actor.organization_id:
        raise BatchConflict("active organization required")
    batch=db.scalar(select(ClaimBatch).where(ClaimBatch.id==batch_id, ClaimBatch.organization_id==actor.organization_id).with_for_update())
    if batch is None or batch.organization_id!=actor.organization_id:
        raise BatchConflict("batch not accessible")
    if batch.status not in ("staged","importing","review_required","imported"):
        raise BatchConflict("invalid batch state")
    doc=_document(db,actor.organization_id,batch.ingestion_document_id)
    if doc.sha256!=batch.source_sha256 or doc.status!="extracted":
        raise BatchConflict("source changed or incomplete")
    job=_job(db,actor.organization_id,doc.id)
    _complete(db, doc, job)
    records, excluded, approval = _eligible(db, actor.organization_id, doc, job, _records(db, job))
    _batch_source(db, batch, job, approval)
    if len(records)!=batch.record_count:
        raise BatchConflict("source record count changed")
    if batch.status=="imported":
        return {"batch_id":batch.id,"status":batch.status,"imported_count":batch.imported_count,
                "record_count":batch.record_count,"excluded_count":len(excluded)}
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
        locator=dict(record.locator)
        if approval:
            locator.update(document_id=doc.id,job_id=job.id,source_sha256=doc.sha256,
                source_scope_approval_id=approval.id,mapping_version=SOURCE_MAPPING_VERSION,
                sheet_type="CLAIMS")
        db.add(ClaimEntry(organization_id=actor.organization_id,batch_id=batch.id,
            extracted_record_id=record.id,source_locator=locator,source_values=record.values,**values))
        batch.imported_count+=1
    db.flush()
    batch.imported_count=db.scalar(select(func.count()).select_from(ClaimEntry).where(ClaimEntry.batch_id==batch.id))
    batch.status="review_required" if rejected else ("imported" if batch.imported_count==batch.record_count else "importing")
    db.add(AuditLog(actor_id=actor.id,action="claim_batch_resumed",resource_type="claim_batch",
        resource_id=batch.id,details={"imported":batch.imported_count,"rejected_count":len(rejected),
                                       "status":batch.status}))
    db.commit()
    return {"batch_id":batch.id,"status":batch.status,"imported_count":batch.imported_count,
            "record_count":batch.record_count,"excluded_count":len(excluded),"rejected":rejected}

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
