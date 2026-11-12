"""Tenant-isolated G4 batch and claim API."""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.models_claims import ClaimBatch, ClaimEntry, ClaimAttachment
from mcias.claim_batches import BatchConflict, stage, preview, resume, attach, source_columns, set_mapping
from mcias.services import claim_reference_service as reference_checks
from mcias.services.authorization_service import check_permission_unified
from mcias.schemas.common import Input
from pydantic import Field
from typing import Literal

router=APIRouter(prefix="/api/v1/claims",tags=["claims"])

class ColumnMapping(Input):
    columns:dict[str,str]=Field(max_length=14)
    currency:str=Field(pattern=r'^[A-Z]{3}$')
    date_format:Literal['ISO','DMY','YMD_SLASH']

@router.get('/batches/{batch_id}/columns')
def columns(batch_id:str,authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    actor=_actor(db,authorization,'claims.import')
    return _run(db,lambda:source_columns(db,actor,batch_id))

@router.put('/batches/{batch_id}/mapping')
def mapping(batch_id:str,payload:ColumnMapping,authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    actor=_actor(db,authorization,'claims.import')
    result=_run(db,lambda:set_mapping(db,actor,batch_id,payload.columns,payload.currency,payload.date_format))
    db.commit();return result

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

def _reference_run(db,fn):
    try:return fn()
    except LookupError:db.rollback();raise HTTPException(404,'Batch or reference check not found') from None
    except ValueError as exc:db.rollback();raise HTTPException(409,str(exc)) from None
    except (RuntimeError,OSError):db.rollback();raise HTTPException(503,'Encrypted reference storage unavailable') from None

def _reference_conflict(batch: ClaimBatch, code: str, reason: str):
    return HTTPException(status_code=409, detail={
        "code": code,
        "batch_id": batch.id,
        "current_status": batch.status,
        "record_count": batch.record_count,
        "imported_count": batch.imported_count,
        "reason": reason,
        "message": f"لا يمكن بدء الفحص المرجعي للدفعة {batch.id}: {reason}",
    })


@router.post('/batches/{batch_id}/reference-checks',status_code=201)
def run_reference_checks(batch_id:str,authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    actor=_actor(db,authorization,'claims.review')
    require_organization(db,actor,actor.organization_id,'claims.read')
    batch=db.scalar(select(ClaimBatch).where(
        ClaimBatch.id==batch_id,
        ClaimBatch.organization_id==actor.organization_id
    ))
    if batch is None:
        raise HTTPException(404, detail={"code":"BATCH_NOT_FOUND","batch_id":batch_id,
                                         "message":"لم يتم العثور على دفعة ضمن مؤسستك."})
    if batch.status != "imported":
        reasons = {
            "staged": "الدفعة مُجهزة فقط؛ اربط الأعمدة ثم أكمل استيراد السجلات.",
            "importing": "الاستيراد لم يكتمل بعد؛ توجد سجلات لم تُستورد.",
            "review_required": "الدفعة تحتاج مراجعة؛ توجد سجلات مرفوضة أو بيانات استخراج غير مكتملة.",
        }
        reason = reasons.get(batch.status, f"حالة الدفعة الحالية ({batch.status}) لا تسمح بالفحص المرجعي.")
        raise _reference_conflict(batch, "BATCH_NOT_IMPORTED", reason)
    if batch.imported_count != batch.record_count:
        raise _reference_conflict(
            batch, "BATCH_IMPORT_COUNT_MISMATCH",
            "حالة الدفعة imported لكن عدد السجلات المستوردة لا يساوي العدد المتوقع؛ يلزم فحص سلامة الاستيراد."
        )
    result=_reference_run(db,lambda:reference_checks.run(db,actor,batch_id))
    db.commit();return result

@router.get('/batches/{batch_id}/reference-checks')
def get_reference_checks(batch_id:str,offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=500),
                         authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    actor=_actor(db,authorization,'claims.read')
    require_organization(db,actor,actor.organization_id,'claims.review')
    result=_reference_run(db,lambda:reference_checks.read(db,actor,batch_id))
    rows=result.pop('rows');return {**result,'rows':rows[offset:offset+limit],'has_more':len(rows)>offset+limit}

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
    result=_run(db,lambda:resume(db,actor,batch_id,chunk_size))
    if result['status']=='imported' and check_permission_unified(db,actor,'claims.review') and check_permission_unified(db,actor,'claims.read'):
        result['reference_check']=_reference_run(db,lambda:reference_checks.run(db,actor,batch_id))
        db.commit()
    else:result['reference_check_required']=True
    return result

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
                    kind:Literal['invoice','supporting']=Query('supporting'),db:Session=Depends(get_db)):
    actor=_actor(db,authorization,"claims.import")
    item=_run(db,lambda:attach(db,actor,claim_id,document_id))
    if kind=='invoice':
        from mcias.services.invoice_service import classify_invoice
        classify_invoice(db,actor,item);db.commit()
    return {"id":item.id,"claim_id":item.claim_id,"document_sha256":item.document_sha256}
