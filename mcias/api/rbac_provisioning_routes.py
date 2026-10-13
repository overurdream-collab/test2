"""Explicit institutional review before group grants become authoritative."""
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy import select
from mcias.api import dependencies as deps
from mcias.schemas.common import Input
from mcias.services import rbac_provisioning as provisioning
from mcias.models_authorization import RbacProvisioning

router=APIRouter(prefix='/api/v1/admin/rbac',tags=['Reviewed RBAC migration'])
class SignedPlan(Input):
    manifest: dict
    approved_by: UUID
    approval_reference: str=Field(min_length=1,max_length=200)
    signature: str=Field(pattern=r'^[0-9a-fA-F]{128}$')
class Configuration(Input):
    group_id: UUID
    permission_ids: list[UUID]=Field(max_length=2000)
    membership_user_ids: list[UUID]=Field(default_factory=list,max_length=2000)

def public(row):
    return {'id':row.id,'organization_id':row.organization_id,'applied_by':row.applied_by,
        'approved_by':row.approved_by,'approval_reference':row.approval_reference,
        'fingerprint':row.fingerprint,'created_at':row.created_at}

@router.get('/migration-preview')
def preview(actor=Depends(deps.require_seed_admin),db=Depends(deps.get_db)):
    return provisioning.preview_migration(db,actor.organization_id)

@router.post('/configuration-preview')
def configuration(payload:Configuration,actor=Depends(deps.require_seed_admin),db=Depends(deps.get_db)):
    try:return provisioning.preview_configuration(db,actor.organization_id,str(payload.group_id),[str(i) for i in payload.permission_ids],[str(i) for i in payload.membership_user_ids])
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(409,'group configuration conflicts with approved scope') from None

@router.post('/apply',status_code=201)
def apply(payload:SignedPlan,actor=Depends(deps.require_seed_admin),db=Depends(deps.get_db)):
    return deps.mutate(db,lambda:provisioning.apply_plan(db,actor.id,payload.model_dump(mode='json')),public)

@router.get('/history')
def history(offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),actor=Depends(deps.require_seed_admin),db=Depends(deps.get_db)):
    rows=list(db.scalars(select(RbacProvisioning).where(RbacProvisioning.organization_id==actor.organization_id).order_by(RbacProvisioning.created_at.desc(),RbacProvisioning.id).offset(offset).limit(limit+1)))
    return {'items':[public(r) for r in rows[:limit]],'offset':offset,'limit':limit,'has_more':len(rows)>limit}
