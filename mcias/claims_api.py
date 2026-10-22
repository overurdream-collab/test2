"""Tenant-isolated G4 batch and claim API."""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.models_claims import ClaimBatch, ClaimEntry, ClaimAttachment
from mcias.claim_batches import BatchConflict, stage, preview, resume, attach, approve_source_scope, sheet_inventory

router=APIRouter(prefix="/api/v1/claims",tags=["claims"])

class SourceScopeApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sheet_types: dict[int, str]

def _actor(db,authorization,permission):
    user,_=resolve_user(db,authorization)
    if not user.organization_id:
        raise HTTPException(403,"organization required")
    require_organization(db,user,user.organization_id,permission)
    return user

def _run(db,fn):
    try:
        return fn()
    except BatchConflict as exc:
        db.rollback()
        raise HTTPException(409,str(exc)) from exc
    except __import__("sqlalchemy").exc.IntegrityError as exc:
        db.rollback()
        raise HTTPException(409,"claim integrity constraint") from exc

@router.get("/documents/{document_id}/worksheet-inventory")
def document_worksheet_inventory(document_id: str, authorization: str | None = Header(default=None),
                                 db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "claims.import")
    return _run(db, lambda: sheet_inventory(db, actor, document_id))


@router.post("/documents/{document_id}/source-scope", status_code=201)
def approve_document_scope(document_id: str, payload: SourceScopeApproval,
                           authorization: str | None = Header(default=None),
                           db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "claims.import")
    approval = _run(db, lambda: approve_source_scope(db, actor, document_id, payload.sheet_types))
    return {"approval_id": approval.id, "document_id": document_id,
            "source_sha256": approval.details["source_sha256"],
            "mapping_version": approval.details["mapping_version"],
            "sheet_types": approval.details["sheet_types"]}

@router.post("/batches/from-document/{document_id}",status_code=201)
def create_batch(document_id: str,authorization: str | None=Header(default=None),
                 db:Session=Depends(get_db)):
    actor=_actor(db,authorization,"claims.import")
    batch=_run(db,lambda:stage(db,actor,document_id))
    return {"id":batch.id,"status":batch.status,"record_count":batch.record_count}

@router.get("/batches/{batch_id}/preview")
def batch_preview(batch_id:str,limit:int=Query(default=100,ge=1,le=500),
                  offset:int=Query(default=0,ge=0),
                  authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    actor=_actor(db,authorization,"claims.read")
    return _run(db,lambda:preview(db,actor,batch_id,limit,offset))

@router.post("/batches/{batch_id}/resume")
def resume_batch(batch_id:str,chunk_size:int=Query(default=100,ge=1,le=1000),
                 authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    actor=_actor(db,authorization,"claims.import")
    return _run(db,lambda:resume(db,actor,batch_id,chunk_size))

@router.get("/batches/{batch_id}")
def get_batch(batch_id:str,authorization:str|None=Header(default=None),
              db:Session=Depends(get_db)):
    actor=_actor(db,authorization,"claims.read")
    batch=db.get(ClaimBatch,batch_id)
    if batch is None or batch.organization_id!=actor.organization_id:
        raise HTTPException(404,"batch not found")
    return {"id":batch.id,"status":batch.status,"record_count":batch.record_count,
            "imported_count":batch.imported_count,"source_sha256":batch.source_sha256}

@router.get("/batches/{batch_id}/entries")
def batch_entries(batch_id:str,limit:int=Query(default=100,ge=1,le=500),
                  offset:int=Query(default=0,ge=0),
                  authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    actor=_actor(db,authorization,"claims.read")
    batch=db.get(ClaimBatch,batch_id)
    if batch is None or batch.organization_id!=actor.organization_id:
        raise HTTPException(404,"batch not found")
    entries=db.scalars(select(ClaimEntry).where(ClaimEntry.batch_id==batch.id,
        ClaimEntry.organization_id==actor.organization_id).order_by(ClaimEntry.id)
        .offset(offset).limit(limit)).all()
    return {"batch_id":batch.id,"entries":[{"id":c.id,"claim_reference":c.claim_reference,
        "source_locator":c.source_locator,"claimed_amount":str(c.claimed_amount),
        "currency":c.currency,"service_date":c.service_date.isoformat()} for c in entries]}

@router.post("/entries/{claim_id}/attachments/{document_id}",status_code=201)
def link_attachment(claim_id:str,document_id:str,authorization:str|None=Header(default=None),
                    db:Session=Depends(get_db)):
    actor=_actor(db,authorization,"claims.import")
    item=_run(db,lambda:attach(db,actor,claim_id,document_id))
    return {"id":item.id,"claim_id":item.claim_id,"document_sha256":item.document_sha256}
