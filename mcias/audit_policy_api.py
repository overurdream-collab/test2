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
from mcias.api.dependencies import require_permission as guard, get_db as session_db
from mcias.schemas.common import Input
from decimal import Decimal
from typing import Literal

router=APIRouter(prefix="/api/v1/audit-policies",tags=["audit-policies"])

class NetDefinition(Input):
    policy_id:str=Field(min_length=1,max_length=120)
    currency:str=Field(pattern='^[A-Z]{3}$')
    rounding:Literal['HALF_UP','HALF_EVEN']
    precision:Literal[0,2,4]
    order:list[str]=Field(min_length=4,max_length=4)
    copay_percent:Decimal=Field(ge=0,le=100)
    cap:Decimal|None=Field(default=None,ge=0)
    exclusion:Decimal=Field(ge=0)
    tariff:Decimal=Field(ge=0)
    approved:Literal[True]
    amount_basis:Literal['NET']
    reference_fingerprint:str=Field(pattern='^[0-9a-f]{64}$')

@router.post('/definitions',status_code=201)
def definition(payload:NetDefinition,actor=Depends(guard('policies.approve')),db=Depends(session_db)):
    from mcias.services.net_audit_service import record_definition
    try:return record_definition(db,actor,payload.model_dump(mode='json'))
    except (PolicyBlocked,ValueError) as exc:db.rollback();raise HTTPException(409,str(exc)) from None

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
