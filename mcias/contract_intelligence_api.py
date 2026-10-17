"""Authorized, preview-only Contract Intelligence API; no financial activation."""
import os
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user, require_permission
from mcias.tenant import require_organization, require_sensitive_field
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord
from mcias.contract_intelligence import (
    ContractExtractionError, make_source_blocks, infer_local, validate_candidates,
)

router = APIRouter(prefix="/api/v1/contract-intelligence", tags=["contract intelligence"])


@router.post("/documents/{document_id}/preview")
def preview(document_id: str, authorization: str | None = Header(default=None),
            db: Session = Depends(get_db)):
    """Fetch G2-verified source only for a permitted organization editor.

    Preview does not write any ReferencePoint, proposal, financial rule or audit.
    There is no remote/cloud fallback. A local operator must configure a model.
    """
    actor, _ = resolve_user(db, authorization)
    if not actor.organization_id:
        raise HTTPException(403, "organization required")
    require_organization(db, actor, actor.organization_id, "reference.write")
    require_permission(db, actor, "workspace.super_admin")
    document = db.get(IngestionDocument, document_id)
    if not document or document.organization_id != actor.organization_id:
        raise HTTPException(404, "source document not found")
    if document.status != "extracted":
        raise HTTPException(409, "source still requires ingestion review")
    job = db.scalar(select(IngestionJob).where(
        IngestionJob.organization_id == actor.organization_id,
        IngestionJob.document_id == document.id,
    ).order_by(IngestionJob.created_at.desc(), IngestionJob.id.desc()))
    if not job or job.status != "extracted" or not job.manifest.get("complete", False):
        raise HTTPException(409, "extraction completeness not established")
    records = db.scalars(select(ExtractedSourceRecord).where(
        ExtractedSourceRecord.job_id == job.id
    ).order_by(ExtractedSourceRecord.id).limit(41)).all()
    if not records or len(records) > 40:
        raise HTTPException(409, "source batch exceeds preview limit or is empty")
    # Preserve G2's sensitive field protections; reference.write alone never
    # grants access to unreviewed medical/contract field values.
    for field in sorted({field for record in records for field in record.values}):
        require_sensitive_field(db, actor, actor.organization_id, field)
    endpoint = os.environ.get("MCIAS_CONTRACT_LLM_URL")
    model = os.environ.get("MCIAS_CONTRACT_LLM_MODEL")
    revision = os.environ.get("MCIAS_CONTRACT_LLM_REVISION")
    if not all((endpoint, model, revision)):
        raise HTTPException(503, "local Contract Intelligence model not configured")
    try:
        blocks = make_source_blocks(records)
        inference = infer_local(blocks, endpoint=endpoint, model_id=model,
                                model_revision=revision)
        items = validate_candidates(
            inference["candidates"], blocks,
            source_sha256=document.sha256, model_id=model, model_revision=revision,
        )
    except ContractExtractionError as exc:
        raise HTTPException(409, "contract extraction unavailable or unsafe") from exc
    # G2 OCR has no numeric independent cross-check. Never treat numeric OCR
    # output as verified; explicit human review even with exact source quote.
    by_record = {r.id: r for r in records}
    for item in items:
        source_record = by_record.get(item["source_record_id"])
        if source_record and source_record.confidence < 100:
            item["validation_errors"] = sorted(set(item["validation_errors"] + ["ocr_uncertain"]))
            item["evidence_status"] = "needs_human_review"
    return {
        "document_id": document.id,
        "source_sha256": document.sha256,
        "model_id": model, "model_revision": revision,
        "request_sha256": inference["request_sha256"],
        "response_sha256": inference["response_sha256"],
        "status": "PREVIEW_ONLY",
        "clauses": items,
    }
