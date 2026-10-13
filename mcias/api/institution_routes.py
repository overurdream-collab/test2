"""Institution workspace: tenant counts and staff management read projections."""
from fastapi import APIRouter, Depends, HTTPException, Query
from mcias.api import dependencies as deps
from mcias.api.features_routes import no_store
from mcias.services import feature_service as features, institution_workspace as workspace

router = APIRouter(prefix='/api/v1/institution', tags=['Institution workspace'], dependencies=[Depends(no_store)])


def guard_feature(db, actor, code):
    if not features.is_super_admin(db, actor) and not features.check_feature(db, actor.organization_id, code):
        raise HTTPException(403, 'organization feature is not enabled')


@router.get('/overview')
def overview(actor=Depends(deps.require_permission('reports.read')), db=Depends(deps.get_db)):
    guard_feature(db, actor, 'dashboard.summary')
    try:
        return workspace.overview(db, actor)
    except (ValueError, RuntimeError):
        raise HTTPException(503, 'reference summary unavailable') from None


@router.get('/users')
def users(q: str = Query('', max_length=120), status: str | None = Query(None, pattern='^(open|closed)$'),
          offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
          actor=Depends(deps.require_permission('users.read')), db=Depends(deps.get_db)):
    guard_feature(db, actor, 'users.list')
    return workspace.user_directory(db, actor, q, status, offset, limit)


@router.get('/assignment-groups')
def groups(actor=Depends(deps.require_permission('users.read', 'groups.read')), db=Depends(deps.get_db)):
    guard_feature(db, actor, 'users.list')
    return {'items': workspace.assignment_groups(db, actor)}
