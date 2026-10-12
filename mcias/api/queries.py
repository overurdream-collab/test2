"""Bounded, tenant-filtered read projections; no mutations or private fields."""
from datetime import date
from fastapi import HTTPException
from sqlalchemy import select
from mcias.models import Group, GroupPermission, Permission, User, UserGroup
from mcias.services import rbac_service as rbac
from mcias.services.rbac_seed import get_all_permissions

CATALOG_CODES = frozenset(p["code"] for p in get_all_permissions())

def scoped(db, model, identifier, actor):
    record = db.scalar(select(model).where(model.id == str(identifier), model.organization_id == actor.organization_id))
    if record is None:
        raise HTTPException(404, "record not found")
    return record

def permission(db, identifier):
    record = db.scalar(select(Permission).where(Permission.id == str(identifier), Permission.code.in_(CATALOG_CODES)))
    if record is None:
        raise HTTPException(404, "permission not found")
    return record

def page(db, query, offset, limit, project=lambda item: item):
    rows = list(db.scalars(query.offset(offset).limit(limit + 1)))
    return {"items": [project(row) for row in rows[:limit]], "offset": offset,
            "limit": limit, "has_more": len(rows) > limit}

def group_members(db, group, offset, limit):
    today = date.today()
    query = select(User.id).join(UserGroup, UserGroup.user_id == User.id).join(Group, Group.id == UserGroup.group_id).where(
        Group.id == group.id, Group.organization_id == group.organization_id,
        User.organization_id == group.organization_id, UserGroup.organization_id == group.organization_id,
        User.active.is_(True), *rbac._live(User, today), *rbac._live(Group, today), *rbac._live(UserGroup, today),
    ).distinct().order_by(User.id)
    return page(db, query, offset, limit)

def group_permissions(db, group, offset, limit):
    today = date.today()
    query = select(Permission.id).join(GroupPermission, GroupPermission.permission_id == Permission.id).join(
        Group, Group.id == GroupPermission.group_id,
    ).where(Group.id == group.id, Group.organization_id == group.organization_id,
            GroupPermission.organization_id == group.organization_id, Permission.code.in_(CATALOG_CODES),
            *rbac._live(Group, today), *rbac._live(GroupPermission, today)).distinct().order_by(Permission.id)
    return page(db, query, offset, limit)
