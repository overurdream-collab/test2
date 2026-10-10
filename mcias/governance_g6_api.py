"""G6 governance evidence API. No financial audit activation is exposed."""
from fastapi import APIRouter,Depends,Header,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.governance_g6 import GovernanceBlocked,open_case,append_event
from mcias.models_governance_g6 import GovernanceCase,GovernanceEvent

router=APIRouter(prefix="/api/v1/governance",tags=["governance"])

class EventRequest(BaseModel):
    kind:str=Field(max_length=32)
    payload:dict=Field(default_factory=dict)
    evidence_document_id:str|None=None

def actor_for(db,authorization):
    actor,_=resolve_user(db,authorization)
    if not actor.organization_id:
        raise HTTPException(403,"organization required")
    return actor

@router.post("/cases/from-audit/{snapshot_id}",status_code=201)
def create_case(snapshot_id:str,authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    actor=actor_for(db,authorization)
    try:
        case=open_case(db,actor,snapshot_id)
        return {"id":case.id,"audit_snapshot_id":case.audit_snapshot_id}
    except GovernanceBlocked as exc:
        db.rollback()
        raise HTTPException(403,str(exc)) from exc

@router.post("/cases/{case_id}/events",status_code=201)
def add_event(case_id:str,body:EventRequest,authorization:str|None=Header(default=None),
              db:Session=Depends(get_db)):
    actor=actor_for(db,authorization)
    try:
        event=append_event(db,actor,case_id,body.kind,body.payload,
            evidence_document_id=body.evidence_document_id)
        return {"id":event.id,"case_id":event.case_id,"version":event.version,"kind":event.kind}
    except GovernanceBlocked as exc:
        db.rollback()
        raise HTTPException(403,str(exc)) from exc

@router.get("/cases/{case_id}")
def case_history(case_id:str,authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    actor=actor_for(db,authorization)
    case=db.scalar(select(GovernanceCase).where(GovernanceCase.id==case_id,
        GovernanceCase.organization_id==actor.organization_id))
    if case is None:
        raise HTTPException(404,"case not found")
    require_organization(db,actor,case.organization_id,"claims.read")
    events=db.scalars(select(GovernanceEvent).where(GovernanceEvent.case_id==case.id,
        GovernanceEvent.organization_id==case.organization_id).order_by(GovernanceEvent.version)).all()
    return {"id":case.id,"claim_id":case.claim_id,"audit_snapshot_id":case.audit_snapshot_id,
        "events":[{"id":e.id,"version":e.version,"kind":e.kind,"actor_id":e.actor_id,
                   "evidence_document_id":e.evidence_document_id,"payload":e.payload} for e in events]}
