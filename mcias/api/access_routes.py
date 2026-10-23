"""Interim direct delegation: the session's super-admin owns administrative grants."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from mcias.api import dependencies as deps
from mcias.api.features_routes import no_store
from mcias.schemas.common import Input
from mcias.services import access_service as service, authorization_service as auth

router = APIRouter(prefix="/api/v1/admin/access", tags=["Super-admin access"], dependencies=[Depends(no_store)])

class Grants(Input):
    codes: list[str] = Field(max_length=300)
    expected_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(min_length=1, max_length=500)

@router.get("/catalog")
def catalog(actor=Depends(deps.require_seed_admin), db=Depends(deps.get_db)):
    return {"authority": auth.authority_mode(), "items": [
        {**p,"delegable":p['code'] not in auth.TECHNICAL_ONLY
            and not p['code'].startswith(("system.","organizations."))}
        for p in service.catalog(db)]}

@router.get("/users/{user_id}")
def get_grants(user_id: UUID, actor=Depends(deps.require_seed_admin), db=Depends(deps.get_db)):
    try: return service.state(db, actor, str(user_id))
    except LookupError: raise HTTPException(404, "User not found") from None

@router.put("/users/{user_id}")
def set_grants(user_id: UUID, payload: Grants, actor=Depends(deps.require_seed_admin), db=Depends(deps.get_db)):
    if auth.authority_mode() != 'super_admin':
        raise HTTPException(409, "Direct grants require super_admin authority mode")
    try:
        result = service.replace_grants(db, actor, str(user_id), payload.codes, payload.expected_revision, payload.reason)
        db.commit(); return result
    except LookupError:
        db.rollback(); raise HTTPException(404, "User not found") from None
    except ValueError as exc:
        db.rollback(); raise HTTPException(409, str(exc)) from None
