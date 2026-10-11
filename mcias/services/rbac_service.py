"""Tenant-bound temporal RBAC operations. Callers own commit and rollback.

Actor IDs must come from a trusted authenticated caller, never a request body.
The existing super_admin role permits technical bootstrap within its own tenant;
it is not an implicit permission grant or a financial authorization.
"""
from contextlib import contextmanager
from datetime import date, datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from mcias.models import (
    AuditLog, Group, GroupPermission, MFAFactor, Permission, Role,
    User, UserGroup, UserPermission, UserRole,
)
from mcias.policy import has_permission as _legacy_permission


def _live(model, today):
    return (
        model.status == "open", model.effective_from <= today,
        or_(model.effective_to.is_(None), model.effective_to > today),
    )


def _live_user(user, today):
    return bool(user and user.active and user.status == "open"
                and user.effective_from and user.effective_from <= today
                and (user.effective_to is None or user.effective_to > today))


@contextmanager
def _atomic(db):
    """Roll back service writes, including audit events, on validation/conflict."""
    try:
        with db.begin_nested():
            yield
            db.flush()
    except IntegrityError as exc:
        raise ValueError("RBAC conflict: duplicate, overlapping period or invalid reference") from exc


def _permission_query(user, today):
    individual = select(UserPermission.permission_id).where(
        UserPermission.user_id == user.id,
        UserPermission.organization_id == user.organization_id,
        *_live(UserPermission, today),
    )
    grouped = select(GroupPermission.permission_id).join(
        Group, Group.id == GroupPermission.group_id,
    ).join(UserGroup, UserGroup.group_id == Group.id).where(
        UserGroup.user_id == user.id,
        UserGroup.organization_id == user.organization_id,
        Group.organization_id == user.organization_id,
        GroupPermission.organization_id == user.organization_id,
        *_live(UserGroup, today), *_live(Group, today), *_live(GroupPermission, today),
    )
    return individual.union(grouped)


def _owns(db, user, code, today):
    if not _live_user(user, today) or not user.organization_id:
        return False
    return db.scalar(select(Permission.id).where(
        Permission.code == code, Permission.id.in_(_permission_query(user, today)),
    ).limit(1)) is not None


def check_permission(db, user_id, permission_code):
    """Check only current individual/group grants, with all tenant links bound."""
    return _owns(db, db.get(User, user_id), permission_code, date.today())


def list_user_permissions(db, user_id):
    today = date.today()
    user = db.get(User, user_id)
    if not _live_user(user, today) or not user.organization_id:
        return []
    return list(db.scalars(select(Permission.id).where(
        Permission.id.in_(_permission_query(user, today)),
    ).distinct().order_by(Permission.id)))


def _super_role(db, user):
    return db.scalar(select(Role.id).join(UserRole, UserRole.role_id == Role.id).where(
        UserRole.user_id == user.id, Role.code == "super_admin",
    ).limit(1)) is not None


def _technical_admin(db, user):
    return _super_role(db, user) and db.scalar(select(MFAFactor.user_id).where(
        MFAFactor.user_id == user.id, MFAFactor.enabled.is_(True),
    )) is not None


def _actor(db, actor_id, organization_id, permissions, today):
    actor = db.scalar(select(User).where(User.id == actor_id).with_for_update())
    if not _live_user(actor, today) or not organization_id or actor.organization_id != organization_id:
        raise ValueError("An active, effective actor in the same organization is required")
    if _technical_admin(db, actor):
        return actor
    for code in permissions:
        if not (_owns(db, actor, code, today) or _legacy_permission(db, actor, code)):
            raise ValueError("Actor lacks required permission: " + code)
    return actor


def _user(db, user_id, organization_id, today, require_active=True):
    user = db.scalar(select(User).where(
        User.id == user_id, User.organization_id == organization_id,
    ).with_for_update())
    if user is None:
        raise ValueError("User is not accessible in this organization")
    if require_active and not _live_user(user, today):
        raise ValueError("User must be active and effective today")
    return user


def _protect_user(db, actor, user):
    if (user.is_super_admin or _super_role(db, user)) and not _technical_admin(db, actor):
        raise ValueError("Only an existing MFA-enabled super_admin may manage privileged accounts")


def _group(db, group_id, today):
    group = db.scalar(select(Group).where(Group.id == group_id).with_for_update())
    if group is None or group.status != "open" or group.effective_from > today or (
        group.effective_to is not None and group.effective_to <= today
    ):
        raise ValueError("An open, effective group is required")
    return group


def _permission(db, permission_id):
    permission = db.get(Permission, permission_id)
    if permission is None:
        raise ValueError("Permission does not exist")
    return permission


def _delegate(db, actor, codes, today):
    technical_admin = _technical_admin(db, actor)
    for code in codes:
        if code.startswith(("system.", "organizations.")):
            raise ValueError("Platform permissions cannot be assigned to institutional users or groups")
        if not technical_admin and not (
            _owns(db, actor, code, today) or _legacy_permission(db, actor, code)
        ):
            raise ValueError("Actor cannot delegate a permission they do not hold: " + code)


def _group_codes(db, group, today):
    return list(db.scalars(select(Permission.code).join(
        GroupPermission, GroupPermission.permission_id == Permission.id,
    ).where(GroupPermission.group_id == group.id,
            GroupPermission.organization_id == group.organization_id,
            GroupPermission.status == "open",
            or_(GroupPermission.effective_to.is_(None), GroupPermission.effective_to > today))))


def _no_overlap(db, model, organization_id, today, **identities):
    # Identity IDs are global; match the exclusion key even if corrupt legacy
    # data carries a different tenant, rather than silently adding another row.
    clauses = [model.status == "open",
               or_(model.effective_to.is_(None), model.effective_to > today)]
    clauses.extend(getattr(model, key) == value for key, value in identities.items())
    existing = db.scalar(select(model).where(*clauses).limit(1).with_for_update())
    if existing is not None and existing.organization_id != organization_id:
        raise ValueError("An existing assignment has an inconsistent organization; review is required")
    if existing is not None:
        raise ValueError("An open or future overlapping assignment already exists")


def _current_assignment(db, model, organization_id, today, **identities):
    clauses = [model.organization_id == organization_id, *_live(model, today)]
    clauses.extend(getattr(model, key) == value for key, value in identities.items())
    rows = list(db.scalars(select(model).where(*clauses).with_for_update()))
    if len(rows) != 1:
        raise ValueError("Exactly one open, effective assignment is required")
    return rows[0]


def _close(record, actor, reason, today):
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("A non-empty closing reason is required")
    if record.status != "open" or record.effective_from > today:
        raise ValueError("Cannot close an already closed or future record")
    record.status = "closed"
    record.effective_to = today
    record.closed_by = actor.id
    record.closed_at = datetime.now(timezone.utc)
    record.close_reason = reason.strip()


def _audit(db, actor, action, resource_type, record, before=None, after=None):
    db.add(AuditLog(
        actor_id=actor.id, actor_username=actor.username,
        organization_id=actor.organization_id, action=action,
        resource_type=resource_type, resource_id=record.id, category="rbac",
        before_state=before, after_state=after,
        details={"organization_id": actor.organization_id},
    ))


def grant_permission_to_group(db, group_id, permission_id, granted_by):
    today = date.today()
    with _atomic(db):
        group = _group(db, group_id, today)
        actor = _actor(db, granted_by, group.organization_id, ("groups.permissions.grant",), today)
        permission = _permission(db, permission_id)
        _delegate(db, actor, (permission.code,), today)
        _no_overlap(db, GroupPermission, group.organization_id, today,
                    group_id=group.id, permission_id=permission.id)
        record = GroupPermission(organization_id=group.organization_id, group_id=group.id,
            permission_id=permission.id, effective_from=today, status="open", version=1, granted_by=actor.id)
        db.add(record)
        db.flush()
        _audit(db, actor, "group_permission.grant", "group_permission", record,
               after={"group_id": group.id, "permission_id": permission.id, "status": "open"})
        return record


def revoke_permission_from_group(db, group_id, permission_id, closed_by, reason):
    today = date.today()
    with _atomic(db):
        group = _group(db, group_id, today)
        actor = _actor(db, closed_by, group.organization_id, ("groups.permissions.revoke",), today)
        _permission(db, permission_id)
        record = _current_assignment(db, GroupPermission, group.organization_id, today,
                                     group_id=group.id, permission_id=permission_id)
        _close(record, actor, reason, today)
        _audit(db, actor, "group_permission.revoke", "group_permission", record,
               before={"status": "open"}, after={"status": "closed", "reason": record.close_reason})
        return record


def add_user_to_group(db, user_id, group_id, added_by):
    today = date.today()
    with _atomic(db):
        group = _group(db, group_id, today)
        actor = _actor(db, added_by, group.organization_id, ("groups.members.add",), today)
        user = _user(db, user_id, group.organization_id, today)
        _protect_user(db, actor, user)
        _delegate(db, actor, _group_codes(db, group, today), today)
        _no_overlap(db, UserGroup, group.organization_id, today, user_id=user.id, group_id=group.id)
        record = UserGroup(organization_id=group.organization_id, user_id=user.id, group_id=group.id,
            effective_from=today, status="open", version=1, added_by=actor.id)
        db.add(record)
        db.flush()
        _audit(db, actor, "user_group.add", "user_group", record,
               after={"user_id": user.id, "group_id": group.id, "status": "open"})
        return record


def remove_user_from_group(db, user_id, group_id, closed_by, reason):
    today = date.today()
    with _atomic(db):
        group = _group(db, group_id, today)
        actor = _actor(db, closed_by, group.organization_id, ("groups.members.remove",), today)
        user = _user(db, user_id, group.organization_id, today, require_active=False)
        _protect_user(db, actor, user)
        record = _current_assignment(db, UserGroup, group.organization_id, today,
                                     user_id=user.id, group_id=group.id)
        _close(record, actor, reason, today)
        _audit(db, actor, "user_group.remove", "user_group", record,
               before={"status": "open"}, after={"status": "closed", "reason": record.close_reason})
        return record


def list_group_members(db, group_id):
    today = date.today()
    group = db.get(Group, group_id)
    if group is None:
        raise ValueError("Group does not exist")
    return list(db.scalars(select(User.id).join(UserGroup, UserGroup.user_id == User.id).join(
        Group, Group.id == UserGroup.group_id,
    ).where(Group.id == group_id, User.organization_id == group.organization_id,
            UserGroup.organization_id == group.organization_id, User.active.is_(True),
            *_live(User, today), *_live(Group, today), *_live(UserGroup, today)
    ).distinct().order_by(User.id)))


def list_user_groups(db, user_id):
    today = date.today()
    user = db.get(User, user_id)
    if not _live_user(user, today) or not user.organization_id:
        return []
    return list(db.scalars(select(Group.id).join(UserGroup, UserGroup.group_id == Group.id).where(
        UserGroup.user_id == user.id, UserGroup.organization_id == user.organization_id,
        Group.organization_id == user.organization_id,
        *_live(Group, today), *_live(UserGroup, today),
    ).distinct().order_by(Group.id)))
