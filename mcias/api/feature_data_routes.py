"""Minimal read bridge for temporal RBAC; legacy services and routes stay intact."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from mcias.api import dependencies as deps, queries
from mcias.api.features_routes import no_store
from mcias.services import feature_service as f

router=APIRouter(prefix="/api/v1/feature-data", tags=["Feature-scoped read projections"], dependencies=[Depends(no_store)])
FEATURES={"claims":"claims.list", "batches":"claims.batches", "contracts":"inputs.contracts",
    "audits":"audit.snapshots", "cases":"governance.cases", "users":"users.list"}

@router.get("/catalog/{kind}")
def catalog(kind: str, offset: int=Query(0,ge=0), limit: int=Query(25,ge=1,le=100),
            actor=Depends(deps.require_auth), db=Depends(deps.get_db)):
    from mcias.workspace_api import CATALOG
    if kind not in CATALOG: raise HTTPException(404,"unsupported catalog")
    model, legacy_permission, fields=CATALOG[kind]
    code=FEATURES.get(kind)
    if code:
        if not f.is_super_admin(db,actor) and not f.check_feature(db,actor.organization_id,code):
            raise HTTPException(403,"organization feature is not enabled")
        if not f.permitted(db,actor,*f.READ_PERMISSIONS[code]): raise HTTPException(403,"permission denied")
    elif not f.permitted(db,actor,legacy_permission): raise HTTPException(403,"permission denied")
    def project(row):
        result={field:getattr(row,field) for field in fields}
        if "claimed_amount" in result:result["claimed_amount"]=str(result["claimed_amount"])
        return result
    order=[model.created_at.desc(),model.id.desc()] if hasattr(model,"created_at") else [model.id]
    return queries.page(db,select(model).where(model.organization_id==actor.organization_id).order_by(*order),offset,limit,project)
