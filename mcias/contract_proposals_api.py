"""Signed-off human review of source-anchored, immutable AI contract candidates.

No model output is accepted from the client. Nothing here approves or changes G3/G5.
"""
import json
from datetime import date
from hashlib import sha256
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user, require_permission
from mcias.tenant import require_organization, require_sensitive_field
from mcias.models import AuditLog
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord
from mcias.models_contract_proposals import ContractProposal, ContractProposalReview, ContractProposalPromotion
from mcias.reference_points import create_draft, PointConflict, as_dict
from mcias.contract_intelligence_api import preview

router=APIRouter(prefix="/api/v1/contract-intelligence",tags=["contract proposals"])

class ReviewRequest(BaseModel):
    decision: str = Field(pattern="^(accepted|rejected)$")
    reason: str = Field(min_length=20,max_length=1000)

def actor_for(db,auth,permission):
    actor,_=resolve_user(db,auth)
    if not actor.organization_id:
        raise HTTPException(403,"organization required")
    require_organization(db,actor,actor.organization_id,permission)
    return actor

def source_gate(db,actor,proposal):
    document=db.get(IngestionDocument,proposal.document_id)
    job=db.get(IngestionJob,proposal.job_id)
    if (not document or document.organization_id!=actor.organization_id or
        document.status!="extracted" or document.sha256!=proposal.candidate.get("source_sha256") or
        not job or job.organization_id!=actor.organization_id or
        job.document_id!=document.id or job.status!="extracted" or
        not job.manifest.get("complete")):
        raise HTTPException(409,"source not independently established")
    record=db.get(ExtractedSourceRecord,proposal.candidate.get("source_record_id"))
    if not record or record.job_id!=job.id:
        raise HTTPException(409,"source anchor unavailable")
    for field in record.values:
        require_sensitive_field(db,actor,actor.organization_id,field)
    return document,record

def scoped(db,actor,proposal_id):
    p=db.get(ContractProposal,proposal_id)
    if not p or p.organization_id!=actor.organization_id:
        raise HTTPException(404,"proposal not found")
    source_gate(db,actor,p)
    return p

def describe(db,p):
    rev=db.scalar(select(ContractProposalReview).where(ContractProposalReview.proposal_id==p.id))
    promoted=db.get(ContractProposalPromotion,p.id)
    return {"id":p.id,"document_id":p.document_id,"candidate":p.candidate,
            "model_id":p.model_id,"model_revision":p.model_revision,
            "review":{"decision":rev.decision,"reason":rev.reason} if rev else None,
            "reference_point_id":promoted.reference_point_id if promoted else None,
            "status":"REFERENCE_DRAFT" if promoted else rev.decision.upper() if rev else "PENDING_REVIEW"}

@router.post("/documents/{document_id}/extract",status_code=201)
def extract(document_id: str,authorization: str|None=Header(default=None),
            db: Session=Depends(get_db)):
    actor=actor_for(db,authorization,"reference.write")
    require_permission(db,actor,"workspace.super_admin")
    result=preview(document_id,authorization,db)
    doc=db.get(IngestionDocument,document_id)
    job=db.scalar(select(IngestionJob).where(
        IngestionJob.organization_id==actor.organization_id,IngestionJob.document_id==doc.id
    ).order_by(IngestionJob.created_at.desc(),IngestionJob.id.desc()))
    if not job:
        raise HTTPException(409,"verified ingestion job missing")
    proposals=[]
    for item in result["clauses"]:
        # Keep only needed provenance and clause. Never copy full extracted source fields.
        candidate={k:v for k,v in item.items() if k!="source_fields"}
        canonical=json.dumps({"source_sha256":doc.sha256,"candidate":candidate},
                             sort_keys=True,ensure_ascii=False,separators=(",",":"))
        digest=sha256(canonical.encode("utf-8")).hexdigest()
        p=db.scalar(select(ContractProposal).where(
            ContractProposal.organization_id==actor.organization_id,
            ContractProposal.document_id==doc.id,ContractProposal.candidate_hash==digest))
        if p is None:
            p=ContractProposal(organization_id=actor.organization_id,document_id=doc.id,
                job_id=job.id,candidate_hash=digest,candidate=candidate,
                model_id=result["model_id"],model_revision=result["model_revision"],
                request_sha256=result["request_sha256"],response_sha256=result["response_sha256"],
                created_by=actor.id)
            db.add(p)
            db.flush()
        proposals.append(p)
    db.add(AuditLog(actor_id=actor.id,action="contract_proposal_extracted",
        resource_type="ingestion_document",resource_id=doc.id,
        details={"proposal_ids":[p.id for p in proposals],"model":result["model_id"],
                 "revision":result["model_revision"],"source_sha256":doc.sha256}))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409,"duplicate extraction race; retry") from exc
    return {"status":"PENDING_HUMAN_REVIEW","proposals":[describe(db,p) for p in proposals]}

@router.get("/documents/{document_id}/proposals")
def list_for_document(document_id: str,authorization: str|None=Header(default=None),
                      db: Session=Depends(get_db)):
    actor=actor_for(db,authorization,"reference.read")
    require_organization(db,actor,actor.organization_id,"ingestion.read")
    doc=db.get(IngestionDocument,document_id)
    if not doc or doc.organization_id!=actor.organization_id:
        raise HTTPException(404,"document not found")
    rows=db.scalars(select(ContractProposal).where(
        ContractProposal.organization_id==actor.organization_id,
        ContractProposal.document_id==doc.id
    ).order_by(ContractProposal.created_at,ContractProposal.id).limit(201)).all()
    if len(rows)>200:
        raise HTTPException(409,"too many proposals; request review pagination")
    for p in rows:
        source_gate(db,actor,p)
    return {"document_id":doc.id,"proposals":[describe(db,p) for p in rows]}

@router.post("/proposals/{proposal_id}/review",status_code=201)
def review(proposal_id: str,payload: ReviewRequest,
           authorization: str|None=Header(default=None),db: Session=Depends(get_db)):
    actor=actor_for(db,authorization,"reference.approve")
    require_organization(db,actor,actor.organization_id,"ingestion.read")
    p=scoped(db,actor,proposal_id)
    if p.created_by==actor.id:
        raise HTTPException(409,"reviewer must be independent of extractor")
    if db.scalar(select(ContractProposalReview).where(ContractProposalReview.proposal_id==p.id)):
        raise HTTPException(409,"review immutable")
    c=p.candidate
    if payload.decision=="accepted" and (
        c.get("validation_errors") or c.get("evidence_status")!="verified_source_anchor"
    ):
        raise HTTPException(409,"unverified candidate requires manual correction")
    rev=ContractProposalReview(proposal_id=p.id,organization_id=actor.organization_id,
        decision=payload.decision,reason=payload.reason.strip(),reviewer_id=actor.id)
    db.add(rev)
    db.add(AuditLog(actor_id=actor.id,action="contract_proposal_reviewed",
        resource_type="contract_proposal",resource_id=p.id,
        details={"decision":payload.decision,"reason":payload.reason.strip()}))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409,"proposal already reviewed") from exc
    return describe(db,p)

@router.post("/proposals/{proposal_id}/promote",status_code=201)
def promote(proposal_id: str,authorization: str|None=Header(default=None),
            db: Session=Depends(get_db)):
    actor=actor_for(db,authorization,"reference.write")
    require_permission(db,actor,"workspace.super_admin")
    p=scoped(db,actor,proposal_id)
    event=db.scalar(select(ContractProposalReview).where(ContractProposalReview.proposal_id==p.id))
    if not event or event.decision!="accepted" or event.reviewer_id==actor.id:
        raise HTTPException(409,"independent accepted review required")
    if db.get(ContractProposalPromotion,p.id):
        raise HTTPException(409,"already promoted")
    c=p.candidate
    if c.get("validation_errors") or c.get("evidence_status")!="verified_source_anchor":
        raise HTTPException(409,"unverified candidate")
    if not c.get("effective_from") or not c.get("effective_until"):
        raise HTTPException(409,"cannot invent a missing effective date")
    try:
        values={"section":c["section"],"logical_key":c["logical_key"],
            "title":c["original_clause_text"][:200],"clause_text":c["original_clause_text"],
            "rule_type":c["rule_type"],"provider_code":c["provider_code"],
            "service_code":c["service_code"],"amount":c["amount"],
            "currency":c["currency"],"effective_from":date.fromisoformat(c["effective_from"]),
            "effective_until":date.fromisoformat(c["effective_until"]),
            "source_document_id":p.document_id,"source_locator":c["source_locator"],
            "supersedes_id":None}
        def note_promotion(point):
            db.add(ContractProposalPromotion(proposal_id=p.id,
                organization_id=actor.organization_id,reference_point_id=point.id,
                promoted_by=actor.id))
            db.add(AuditLog(actor_id=actor.id,action="contract_proposal_promoted_draft_only",
                resource_type="reference_point",resource_id=point.id,
                details={"proposal_id":p.id}))
        point=create_draft(db,actor,values,on_created=note_promotion)
    except (PointConflict,ValueError,KeyError,TypeError,IntegrityError) as exc:
        db.rollback()
        raise HTTPException(409,"draft promotion blocked") from exc
    return {"status":"REFERENCE_DRAFT_ONLY","reference_point":as_dict(point),
            "financial_execution_authorized":False}
