"""G5 institutional approval lifecycle API.

A client cannot supply a financial policy to execute a claim audit.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.audit_engine import PolicyBlocked
from mcias.audit_policy_lifecycle import enroll_grant, revoke_grant

router=APIRouter(prefix="/api/v1/audit-policies",tags=["audit-policies"])

class GrantRequest(BaseModel):
    organization_id:str=Field(min_length=1,max_length=36)
    policy_id:str=Field(min_length=1,max_length=120)
    policy_fingerprint:str=Field(pattern=r"^[0-9a-f]{64}$")
    approver_id:str=Field(min_length=1,max_length=36)
    reviewer_id:str=Field(min_length=1,max_length=36)
    signature:str=Field(pattern=r"^[0-9a-f]{64}$")

@router.post("/grants",status_code=201)
def create_grant(payload:GrantRequest,authorization:str|None=Header(default=None),
                 db:Session=Depends(get_db)):
    actor,_=resolve_user(db,authorization)
    try:
        grant=enroll_grant(db,actor=actor,**payload.model_dump())
    except PolicyBlocked as exc:
        db.rollback()
        raise HTTPException(403,str(exc)) from exc
    return {"id":grant.id,"policy_id":grant.policy_id,"revoked":False}

@router.post("/grants/{grant_id}/revoke")
def revoke(grant_id:str,authorization:str|None=Header(default=None),
           db:Session=Depends(get_db)):
    actor,_=resolve_user(db,authorization)
    try:
        grant=revoke_grant(db,actor=actor,grant_id=grant_id)
    except PolicyBlocked as exc:
        db.rollback()
        raise HTTPException(403,str(exc)) from exc
    return {"id":grant.id,"revoked":True}
