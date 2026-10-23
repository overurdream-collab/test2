"""Explicit per-line invoice links; classification is not automatic OCR review."""
from sqlalchemy import select
from cryptography.exceptions import InvalidTag
from mcias.models import AuditLog, SourceFile
from mcias.models_claims import ClaimAttachment, ClaimBatch
from mcias.models_ingestion import IngestionDocument
from mcias.services.registry_service import store

def classify_invoice(db,actor,attachment):
    if attachment.organization_id!=actor.organization_id:raise ValueError('Invoice scope mismatch')
    existing=db.scalar(select(AuditLog.id).where(AuditLog.organization_id==actor.organization_id,
        AuditLog.action=='claim_invoice.linked',AuditLog.resource_id==attachment.id))
    if not existing:
        db.add(AuditLog(actor_id=actor.id,organization_id=actor.organization_id,
            action='claim_invoice.linked',resource_type='claim_attachment',resource_id=attachment.id,
            category='invoice_evidence',details={'claim_id':attachment.claim_id,
                'document_id':attachment.ingestion_document_id,'sha256':attachment.document_sha256,
                'classification':'operator_linked_invoice'}));db.flush()

def invoices(db,claim):
    events=list(db.scalars(select(AuditLog).where(AuditLog.organization_id==claim.organization_id,
        AuditLog.action=='claim_invoice.linked',AuditLog.details['claim_id'].as_string()==claim.id)))
    evidence=[]
    batch=db.get(ClaimBatch,claim.batch_id)
    for event in events:
        link=db.get(ClaimAttachment,event.resource_id)
        if not link or link.organization_id!=claim.organization_id or link.claim_id!=claim.id:continue
        document=db.get(IngestionDocument,link.ingestion_document_id)
        if (not document or document.organization_id!=claim.organization_id or document.status!='extracted'
                or (batch and document.id==batch.ingestion_document_id)
                or not document.filename.lower().endswith(('.pdf','.png','.jpg','.jpeg'))
                or document.sha256!=link.document_sha256 or event.details.get('sha256')!=document.sha256
                or event.details.get('document_id')!=document.id):continue
        source=db.get(SourceFile,document.source_id)
        if not source or source.sha256!=document.sha256:continue
        try:store().get(source.storage_key,source.sha256)
        except (ValueError,OSError,InvalidTag):continue
        evidence.append({'attachment_id':link.id,'document_id':document.id,'sha256':source.sha256,
            'classification':'operator_linked_invoice','classified_by':event.actor_id})
    return sorted(evidence,key=lambda r:r['attachment_id'])
