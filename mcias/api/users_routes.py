from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from mcias.api import dependencies as deps, queries
from mcias.models import Group, Permission, User
from mcias.schemas.common import Close, Page, PermissionGrant, UserGroupRead, UserPermissionRead
from mcias.schemas.permission import PermissionRead
from mcias.schemas.user import GroupTransfer, UserCreate, UserRead
from mcias.security import hash_password
from mcias.services import rbac_service as rbac, user_lifecycle as users

router = APIRouter(prefix="/api/v1/users", tags=["RBAC users"])

@router.get("", response_model=Page[UserRead])
def list_users(offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
               actor=Depends(deps.require_permission("users.read")), db=Depends(deps.get_db)):
    return queries.page(db, select(User).where(User.organization_id == actor.organization_id).order_by(User.username, User.id),
                        offset, limit, UserRead.model_validate)

@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, actor=Depends(deps.require_permission("users.create")), db=Depends(deps.get_db)):
    return deps.mutate(db, lambda: users.create_user(db, actor.organization_id, payload.username,
        hash_password(payload.password.get_secret_value()), actor.id, payload.full_name_ar, payload.email), UserRead.model_validate)

@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: UUID, actor=Depends(deps.require_permission("users.read")), db=Depends(deps.get_db)):
    return queries.scoped(db, User, user_id, actor)

@router.post("/{user_id}/close", response_model=UserRead)
def close_user(user_id: UUID, payload: Close, actor=Depends(deps.require_permission("users.close")), db=Depends(deps.get_db)):
    user = queries.scoped(db, User, user_id, actor)
    deps.protect_user(db, actor, user)
    return deps.mutate(db, lambda: users.close_user(db, user.id, actor.id, payload.reason), UserRead.model_validate)

@router.get("/{user_id}/permissions", response_model=Page[PermissionRead])
def user_permissions(user_id: UUID, offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
                     actor=Depends(deps.require_permission("users.read")), db=Depends(deps.get_db)):
    user = queries.scoped(db, User, user_id, actor)
    identifiers = rbac.list_user_permissions(db, user.id)
    query = select(Permission).where(Permission.id.in_(identifiers), Permission.code.in_(queries.CATALOG_CODES)).order_by(Permission.code)
    return queries.page(db, query, offset, limit, PermissionRead.model_validate)

@router.post("/{user_id}/permissions", response_model=UserPermissionRead, status_code=201)
def grant_permission(user_id: UUID, payload: PermissionGrant,
                     actor=Depends(deps.require_permission("users.permissions.grant")), db=Depends(deps.get_db)):
    user = queries.scoped(db, User, user_id, actor)
    permission = queries.permission(db, payload.permission_id)
    deps.protect_user(db, actor, user)
    deps.delegate(db, actor, (permission.code,))
    return deps.mutate(db, lambda: users.grant_user_permission(db, user.id, permission.id, actor.id), UserPermissionRead.model_validate)

@router.post("/{user_id}/permissions/{permission_id}/revoke", response_model=UserPermissionRead)
def revoke_permission(user_id: UUID, permission_id: UUID, payload: Close,
                      actor=Depends(deps.require_permission("users.permissions.revoke")), db=Depends(deps.get_db)):
    user = queries.scoped(db, User, user_id, actor)
    permission = queries.permission(db, permission_id)
    deps.protect_user(db, actor, user)
    return deps.mutate(db, lambda: users.revoke_user_permission(db, user.id, permission.id, actor.id, payload.reason), UserPermissionRead.model_validate)

@router.post("/{user_id}/group-transfers", response_model=UserGroupRead)
def transfer_group(user_id: UUID, payload: GroupTransfer,
                   actor=Depends(deps.require_permission("groups.members.remove", "groups.members.add")), db=Depends(deps.get_db)):
    user = queries.scoped(db, User, user_id, actor)
    source = queries.scoped(db, Group, payload.from_group_id, actor)
    destination = queries.scoped(db, Group, payload.to_group_id, actor)
    deps.protect_user(db, actor, user)
    from datetime import date
    deps.delegate(db, actor, rbac._group_codes(db, destination, date.today()))
    return deps.mutate(db, lambda: users.change_user_group(db, user.id, source.id, destination.id, actor.id, payload.reason), UserGroupRead.model_validate)
