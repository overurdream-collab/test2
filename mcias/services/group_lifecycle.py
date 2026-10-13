"""Group creation/closure only. Callers own commit and rollback."""
from datetime import date
from sqlalchemy import select
from mcias.models import Group
from mcias.services import rbac_service as rbac

def create_group(db, organization_id, code, name_ar, created_by, name_en=None, description=None, management_scope="functional"):
    with rbac._atomic(db):
        actor = rbac._actor(db, created_by, organization_id, ("groups.create",), date.today())
        if management_scope not in ("functional","institution_admin"):
            raise ValueError("Invalid group scope")
        if db.scalar(select(Group.id).where(Group.organization_id == organization_id, Group.code == code).limit(1)) is not None:
            raise ValueError("Group code already exists; closed groups require a new code")
        group = Group(organization_id=organization_id, code=code, name_ar=name_ar,
            name_en=name_en, description=description, is_system=False, management_scope=management_scope,
            status="open", effective_from=date.today(), version=1, created_by=actor.id)
        db.add(group)
        db.flush()
        rbac._audit(db, actor, "group.create", "group", group, after={"code": group.code, "status": "open"})
        return group

def close_group(db, group_id, closed_by, reason):
    today = date.today()
    with rbac._atomic(db):
        group = rbac._group(db, group_id, today)
        actor = rbac._actor(db, closed_by, group.organization_id, ("groups.close",), today)
        rbac._close(group, actor, reason, today)
        rbac._audit(db, actor, "group.close", "group", group,
            before={"status": "open"}, after={"status": "closed", "reason": group.close_reason})
        return group
