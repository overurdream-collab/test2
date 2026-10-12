"""Feature administration is technical only; never a financial approval bypass."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from pydantic import Field
from sqlalchemy import select
from mcias.api import dependencies as deps, queries
from mcias.models import Organization
from mcias.schemas.common import Close, Input
from mcias.services import feature_service as features

def no_store(response: Response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

router = APIRouter(tags=["Organization features"], dependencies=[Depends(no_store)])

class FeatureBatch(Input):
    codes: list[str] = Field(max_length=33)
    expected_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(default="", max_length=2000)

def admin(actor=Depends(deps.require_auth), db=Depends(deps.get_db)):
    # Narrow, existing MFA super-admin bootstrap for technical feature governance.
    # Does not grant platform permissions to tenant groups or financial authority.
    if not features.is_super_admin(db, actor):
        raise HTTPException(403, "MFA-enabled super_admin required")
    return actor

def _organization(db, org_id, actor):
    if not features.is_super_admin(db, actor) and actor.organization_id != str(org_id):
        raise HTTPException(404, "organization not found")
    if db.get(Organization, str(org_id)) is None:
        raise HTTPException(404, "organization not found")

def project(row):
    return {name: getattr(row, name) for name in ("id", "feature_code", "status", "effective_from", "effective_to", "version")}

def state(db, org_id):
    return {"items": [project(r) for r in features.get_org_features(db, org_id)],
        "revision": features.grant_revision(db, org_id)}

@router.get("/admin/features")
def catalog(actor=Depends(admin), db=Depends(deps.get_db)):
    return {"items": [{k: getattr(r, k) for k in ("code", "category", "parent_code", "name_ar", "name_en", "is_container", "display_order")}
        for r in features.list_features(db)]}

@router.get("/admin/features/tree")
def tree(actor=Depends(admin), db=Depends(deps.get_db)):
    return {"items": features.list_feature_tree(db)}

@router.get("/admin/feature-organizations")
def organizations(offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
                  actor=Depends(admin), db=Depends(deps.get_db)):
    return queries.page(db, select(Organization).order_by(Organization.name, Organization.id), offset, limit,
        lambda r: {"id": r.id, "name": r.name})

@router.get("/organizations/{org_id}/features")
def organization_features(org_id: UUID, actor=Depends(deps.require_auth), db=Depends(deps.get_db)):
    _organization(db, org_id, actor)
    return state(db, str(org_id))

@router.post("/organizations/{org_id}/features/{code}/grant", status_code=201)
def grant(org_id: UUID, code: str, actor=Depends(admin), db=Depends(deps.get_db)):
    _organization(db, org_id, actor)
    return deps.mutate(db, lambda: features.grant_feature(db, str(org_id), code, actor.id), project)

@router.post("/organizations/{org_id}/features/{code}/revoke")
def revoke(org_id: UUID, code: str, payload: Close, actor=Depends(admin), db=Depends(deps.get_db)):
    _organization(db, org_id, actor)
    return deps.mutate(db, lambda: features.revoke_feature(db, str(org_id), code, actor.id, payload.reason), project)

@router.put("/organizations/{org_id}/features")
def batch(org_id: UUID, payload: FeatureBatch, actor=Depends(admin), db=Depends(deps.get_db)):
    _organization(db, org_id, actor)
    return deps.mutate(db, lambda: features.replace_features(db, str(org_id), payload.codes, actor.id,
        payload.reason, payload.expected_revision), lambda _: state(db, str(org_id)))

@router.get("/me/features")
def mine(request: Request, response: Response, actor=Depends(deps.require_auth), db=Depends(deps.get_db)):
    response.headers["Cache-Control"] = "no-store"
    return {"organization_id": actor.organization_id, "features": features.get_visible_features(db, actor),
        "permissions": features.permission_codes(db, actor), "super_admin": features.is_super_admin(db, actor),
        "expires_at": request.state.rbac_session_expires_at,
        "user": {"id": actor.id, "username": actor.username},
        "organization": {"id": actor.organization_id, "name": db.get(Organization, actor.organization_id).name},
        "roles": ["super_admin"] if features.is_super_admin(db, actor) else []}
