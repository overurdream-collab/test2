from fastapi import APIRouter, Depends
from mcias.api import dependencies as deps
from mcias.schemas.common import Input, SeedRead
from mcias.services.rbac_seed import seed_organization

router = APIRouter(prefix="/api/v1/rbac", tags=["RBAC initialization"])

@router.post("/seed", response_model=SeedRead)
def seed(payload: Input | None = None, actor=Depends(deps.require_seed_admin), db=Depends(deps.get_db)):
    return deps.mutate(db, lambda: seed_organization(db, actor.organization_id, actor.id), SeedRead.model_validate)
