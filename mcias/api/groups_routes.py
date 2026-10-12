from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from mcias.api import dependencies as deps, queries
from mcias.models import Group, User
from mcias.schemas.common import Close, GroupPermissionRead, MemberAdd, Page, PermissionGrant, UserGroupRead
from mcias.schemas.group import GroupCreate, GroupDetail, GroupRead
from mcias.services import group_lifecycle as groups, rbac_service as rbac

router = APIRouter(prefix="/api/v1/groups", tags=["RBAC groups"])

@router.get("", response_model=Page[GroupRead])
def list_groups(offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
                actor=Depends(deps.require_permission("groups.read")), db=Depends(deps.get_db)):
    return queries.page(db, select(Group).where(Group.organization_id == actor.organization_id).order_by(Group.code, Group.id),
                        offset, limit, GroupRead.model_validate)

@router.post("", response_model=GroupRead, status_code=201)
def create_group(payload: GroupCreate, actor=Depends(deps.require_permission("groups.create")), db=Depends(deps.get_db)):
    return deps.mutate(db, lambda: groups.create_group(db, actor.organization_id, payload.code,
        payload.name_ar, actor.id, payload.name_en, payload.description), GroupRead.model_validate)

@router.get("/{group_id}", response_model=GroupDetail)
def get_group(group_id: UUID, member_offset: int = Query(0, ge=0), member_limit: int = Query(25, ge=1, le=100),
              permission_offset: int = Query(0, ge=0), permission_limit: int = Query(25, ge=1, le=100),
              actor=Depends(deps.require_permission("groups.read")), db=Depends(deps.get_db)):
    group = queries.scoped(db, Group, group_id, actor)
    return {**GroupRead.model_validate(group).model_dump(),
            "members": queries.group_members(db, group, member_offset, member_limit),
            "permission_ids": queries.group_permissions(db, group, permission_offset, permission_limit)}

@router.post("/{group_id}/close", response_model=GroupRead)
def close_group(group_id: UUID, payload: Close, actor=Depends(deps.require_permission("groups.close")), db=Depends(deps.get_db)):
    group = queries.scoped(db, Group, group_id, actor)
    return deps.mutate(db, lambda: groups.close_group(db, group.id, actor.id, payload.reason), GroupRead.model_validate)

@router.post("/{group_id}/members", response_model=UserGroupRead, status_code=201)
def add_member(group_id: UUID, payload: MemberAdd,
               actor=Depends(deps.require_permission("groups.members.add")), db=Depends(deps.get_db)):
    group = queries.scoped(db, Group, group_id, actor)
    user = queries.scoped(db, User, payload.user_id, actor)
    deps.protect_user(db, actor, user)
    deps.delegate(db, actor, rbac._group_codes(db, group, date.today()))
    return deps.mutate(db, lambda: rbac.add_user_to_group(db, user.id, group.id, actor.id), UserGroupRead.model_validate)

@router.post("/{group_id}/members/{user_id}/remove", response_model=UserGroupRead)
def remove_member(group_id: UUID, user_id: UUID, payload: Close,
                  actor=Depends(deps.require_permission("groups.members.remove")), db=Depends(deps.get_db)):
    group = queries.scoped(db, Group, group_id, actor)
    user = queries.scoped(db, User, user_id, actor)
    deps.protect_user(db, actor, user)
    return deps.mutate(db, lambda: rbac.remove_user_from_group(db, user.id, group.id, actor.id, payload.reason), UserGroupRead.model_validate)

@router.post("/{group_id}/permissions", response_model=GroupPermissionRead, status_code=201)
def grant_permission(group_id: UUID, payload: PermissionGrant,
                     actor=Depends(deps.require_permission("groups.permissions.grant")), db=Depends(deps.get_db)):
    group = queries.scoped(db, Group, group_id, actor)
    permission = queries.permission(db, payload.permission_id)
    deps.delegate(db, actor, (permission.code,))
    return deps.mutate(db, lambda: rbac.grant_permission_to_group(db, group.id, permission.id, actor.id), GroupPermissionRead.model_validate)

@router.post("/{group_id}/permissions/{permission_id}/revoke", response_model=GroupPermissionRead)
def revoke_permission(group_id: UUID, permission_id: UUID, payload: Close,
                      actor=Depends(deps.require_permission("groups.permissions.revoke")), db=Depends(deps.get_db)):
    group = queries.scoped(db, Group, group_id, actor)
    permission = queries.permission(db, permission_id)
    return deps.mutate(db, lambda: rbac.revoke_permission_from_group(db, group.id, permission.id, actor.id, payload.reason), GroupPermissionRead.model_validate)
