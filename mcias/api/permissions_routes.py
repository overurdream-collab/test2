from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from mcias.api import dependencies as deps, queries
from mcias.models import Permission, Role, UserRole
from mcias.schemas.common import Page
from mcias.schemas.permission import PermissionContext, PermissionRead
from mcias.schemas.user import UserRead
from mcias.services import rbac_service as rbac

router = APIRouter(prefix="/api/v1/permissions", tags=["RBAC permissions"])

@router.get("", response_model=Page[PermissionRead])
def list_permissions(offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
                     actor=Depends(deps.require_permission("permissions.read")), db=Depends(deps.get_db)):
    return queries.page(db, select(Permission).where(Permission.code.in_(queries.CATALOG_CODES)).order_by(Permission.code),
                        offset, limit, PermissionRead.model_validate)

@router.get("/me", response_model=PermissionContext)
def my_permissions(request: Request, actor=Depends(deps.require_auth), db=Depends(deps.get_db)):
    effective_ids = rbac.list_user_permissions(db, actor.id)
    permissions = list(db.scalars(select(Permission).where(Permission.id.in_(effective_ids)).order_by(Permission.code)))
    roles = list(db.scalars(select(Role.code).join(UserRole, UserRole.role_id == Role.id).where(
        UserRole.user_id == actor.id).distinct().order_by(Role.code)))
    return PermissionContext(user=UserRead.model_validate(actor), permission_ids=[p.id for p in permissions],
        permission_codes=[p.code for p in permissions], group_ids=rbac.list_user_groups(db, actor.id),
        legacy_roles=roles, technical_rbac_admin=rbac._technical_admin(db, actor),
        expires_at=request.state.rbac_session_expires_at)

@router.get("/{permission_id}", response_model=PermissionRead)
def get_permission(permission_id: UUID, actor=Depends(deps.require_permission("permissions.read")), db=Depends(deps.get_db)):
    return queries.permission(db, permission_id)
