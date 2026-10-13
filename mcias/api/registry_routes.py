"""Feature- and permission-gated encrypted intake for sixteen reference sections."""
from uuid import UUID
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from sqlalchemy.exc import DBAPIError
from mcias.api import dependencies as deps
from mcias.api.features_routes import no_store
from mcias.schemas.registry import RecordCreate, RecordVersion, RecordClose, ImportCommit, SCHEMAS, FIELDS, FIELD_LIMITS
from mcias.services import registry_service as r
from mcias.services.feature_service import permitted
from mcias.ingestion.orchestrator import ingest
from mcias.models_ingestion import IngestionDocument
from mcias.models import SourceFile

router=APIRouter(prefix="/api/v1/registry",tags=["Encrypted reference intake"],dependencies=[Depends(no_store)])

def perform(db,action):
    try: result=action();db.commit();return result
    except r.RegistryForbidden as exc: db.rollback();raise HTTPException(403,str(exc)) from None
    except r.RegistryMissing as exc: db.rollback();raise HTTPException(404,str(exc)) from None
    except ValueError as exc: db.rollback();raise HTTPException(409,str(exc)) from None
    except (DBAPIError,RuntimeError): db.rollback();raise HTTPException(503,"intake storage unavailable") from None

@router.get("/{feature}/schema")
def schema(feature:str,actor=Depends(deps.require_auth),db=Depends(deps.get_db)):
    perform(db,lambda:r.authorize(db,actor,feature))
    return {"feature":feature,"fields":[{"key":key,"ar":FIELDS[key][0],"en":FIELDS[key][1],"type":FIELDS[key][2],"max_length":FIELD_LIMITS.get(key,200)} for key in SCHEMAS[feature]],
        "permissions":{operation:permitted(db,actor,*(tuple(c[:-5]+'.'+operation for c in r.f.READ_PERMISSIONS[feature] if c.endswith('.read'))+('reference.write',))) for operation in ('create','close')},
        "approval_required":True,"financially_active":False}

@router.get("/{feature}/records")
def records(feature:str,q:str=Query('',max_length=200),status:str|None=Query(None,pattern=r'^(open|closed)$'),
            offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),actor=Depends(deps.require_auth),db=Depends(deps.get_db)):
    return perform(db,lambda:r.list_records(db,actor,feature,q,status,offset,limit))

@router.post("/{feature}/records",status_code=201)
def create(feature:str,payload:RecordCreate,actor=Depends(deps.require_auth),db=Depends(deps.get_db)):
    return perform(db,lambda:r.create_record(db,actor,feature,payload))

@router.get("/{feature}/records/{record_id}")
def detail(feature:str,record_id:UUID,actor=Depends(deps.require_auth),db=Depends(deps.get_db)):
    return perform(db,lambda:r.read_record(db,actor,feature,str(record_id)))

@router.get("/{feature}/records/{record_id}/history")
def history(feature:str,record_id:UUID,actor=Depends(deps.require_auth),db=Depends(deps.get_db)):
    return {"items":perform(db,lambda:r.record_history(db,actor,feature,str(record_id)))}

@router.post("/{feature}/records/{record_id}/close")
def close(feature:str,record_id:UUID,payload:RecordClose,actor=Depends(deps.require_auth),db=Depends(deps.get_db)):
    return perform(db,lambda:r.close_record(db,actor,feature,str(record_id),payload.expected_version,payload.reason))

@router.post("/{feature}/records/{record_id}/versions",status_code=201)
def version(feature:str,record_id:UUID,payload:RecordVersion,actor=Depends(deps.require_auth),db=Depends(deps.get_db)):
    return perform(db,lambda:r.create_record(db,actor,feature,payload,str(record_id),payload.expected_version))

@router.post("/{feature}/imports",status_code=201)
async def upload(feature:str,request:Request,filename:str=Query(...,min_length=1,max_length=200),actor=Depends(deps.require_auth),db=Depends(deps.get_db)):
    perform(db,lambda:r.authorize(db,actor,feature,"create"))
    if not permitted(db,actor,"ingestion.upload"):raise HTTPException(403,"upload permission required")
    if Path(filename).suffix.lower() not in ('.csv','.xlsx','.pdf'):raise HTTPException(422,"CSV, XLSX or PDF required")
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>20*1024*1024:raise HTTPException(413,"source exceeds upload limit")
    if not data:raise HTTPException(422,"nonempty source required")
    return await run_in_threadpool(perform,db,lambda:ingest(db,r.store(),actor.organization_id,actor.id,filename,bytes(data)))

@router.get("/{feature}/imports/{document_id}/preview")
def preview(feature:str,document_id:UUID,actor=Depends(deps.require_auth),db=Depends(deps.get_db)):
    return perform(db,lambda:r.preview_import(db,actor,feature,str(document_id)))

@router.post("/{feature}/imports/{document_id}/commit",status_code=201)
def confirm(feature:str,document_id:UUID,payload:ImportCommit,actor=Depends(deps.require_auth),db=Depends(deps.get_db)):
    return {"items":perform(db,lambda:r.commit_import(db,actor,feature,str(document_id),payload.record_ids,payload.manual_record))}

@router.get("/{feature}/records/{record_id}/evidence/{document_id}")
def evidence(feature:str,record_id:UUID,document_id:UUID,actor=Depends(deps.require_auth),db=Depends(deps.get_db)):
    def download():
        record=r.read_record(db,actor,feature,str(record_id))
        if not record.get('evidence') or record['evidence']['document_id']!=str(document_id):raise r.RegistryMissing('evidence not linked')
        doc=db.get(IngestionDocument,str(document_id))
        if not doc or doc.organization_id!=actor.organization_id:raise r.RegistryMissing('evidence not found')
        source=db.get(SourceFile,doc.source_id)
        if not source or source.sha256!=record['evidence']['sha256']:raise ValueError('evidence hash mismatch')
        return r.store().get(source.storage_key,source.sha256)
    data=perform(db,download)
    doc=db.get(IngestionDocument,str(document_id))
    extension=Path(doc.filename).suffix.lower()
    if extension not in ('.csv','.xlsx','.pdf'):extension='.bin'
    return Response(data,media_type='application/octet-stream',headers={'Cache-Control':'no-store',
        'Content-Disposition':f'attachment; filename="source-{document_id}{extension}"','X-Content-Type-Options':'nosniff'})
