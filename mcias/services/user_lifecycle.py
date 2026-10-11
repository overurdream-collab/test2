"""User lifecycle services; no commits, deletions, reopening or API changes."""
from datetime import date

from sqlalchemy import select

from mcias.models import Organization, User, UserPermission
from mcias.services import rbac_service as rbac


def create_user(db, organization_id, username, password_hash, created_by, full_name_ar=None, email=None):
    today = date.today()
    with rbac._atomic(db):
        actor = rbac._actor(db, created_by, organization_id, ("users.create",), today)
        if db.get(Organization, organization_id) is None:
            raise ValueError("Organization does not exist")
        if not isinstance(username, str) or not username.strip() or username != username.strip() or len(username) > 120:
            raise ValueError("Username must be non-empty, at most 120 characters and without surrounding whitespace")
        if not isinstance(password_hash, str) or not password_hash:
            raise ValueError("A precomputed password hash is required")
        for value, label in ((full_name_ar, "Arabic full name"), (email, "Email")):
            if value is not None and (not isinstance(value, str) or len(value) > 200):
                raise ValueError(label + " must be at most 200 characters")
        if db.scalar(select(User.id).where(User.username == username)) is not None:
            raise ValueError("Username already exists; closed accounts cannot be reused")
        user = User(organization_id=organization_id, username=username, password_hash=password_hash,
            full_name_ar=full_name_ar, email=email, status="open", effective_from=today,
            version=1, is_super_admin=False, active=True)
        db.add(user)
        db.flush()
        rbac._audit(db, actor, "user.create", "user", user,
                    after={"username": user.username, "status": "open", "organization_id": organization_id})
        return user


def close_user(db, user_id, closed_by, reason):
    today = date.today()
    with rbac._atomic(db):
        target = db.get(User, user_id)
        if target is None:
            raise ValueError("User does not exist")
        actor = rbac._actor(db, closed_by, target.organization_id, ("users.close",), today)
        user = rbac._user(db, user_id, actor.organization_id, today, require_active=False)
        rbac._protect_user(db, actor, user)
        rbac._close(user, actor, reason, today)
        user.active = False
        rbac._audit(db, actor, "user.close", "user", user,
                    before={"status": "open"}, after={"status": "closed", "active": False, "reason": user.close_reason})
        return user


def reopen_user(db, user_id, reopened_by, reason):
    raise ValueError("أنشئ مستخدماً جديداً؛ لا يمكن إعادة فتح سجل مغلق")


def change_user_group(db, user_id, from_group_id, to_group_id, changed_by, reason):
    today = date.today()
    with rbac._atomic(db):
        if from_group_id == to_group_id:
            raise ValueError("Source and destination groups must differ")
        source = rbac._group(db, from_group_id, today)
        actor = rbac._actor(db, changed_by, source.organization_id,
                            ("groups.members.remove", "groups.members.add"), today)
        rbac.remove_user_from_group(db, user_id, from_group_id, actor.id, reason)
        new = rbac.add_user_to_group(db, user_id, to_group_id, actor.id)
        rbac._audit(db, actor, "user_group.change", "user_group", new,
                    before={"group_id": from_group_id}, after={"group_id": to_group_id, "reason": reason.strip()})
        return new


def grant_user_permission(db, user_id, permission_id, granted_by):
    today = date.today()
    with rbac._atomic(db):
        target = db.get(User, user_id)
        if target is None:
            raise ValueError("User does not exist")
        actor = rbac._actor(db, granted_by, target.organization_id, ("users.permissions.grant",), today)
        user = rbac._user(db, user_id, actor.organization_id, today)
        rbac._protect_user(db, actor, user)
        permission = rbac._permission(db, permission_id)
        rbac._delegate(db, actor, (permission.code,), today)
        rbac._no_overlap(db, UserPermission, user.organization_id, today,
                         user_id=user.id, permission_id=permission.id)
        record = UserPermission(organization_id=user.organization_id, user_id=user.id,
            permission_id=permission.id, granted_by=actor.id, status="open", effective_from=today, version=1)
        db.add(record)
        db.flush()
        rbac._audit(db, actor, "user_permission.grant", "user_permission", record,
                    after={"user_id": user.id, "permission_id": permission.id, "status": "open"})
        return record


def revoke_user_permission(db, user_id, permission_id, closed_by, reason):
    today = date.today()
    with rbac._atomic(db):
        target = db.get(User, user_id)
        if target is None:
            raise ValueError("User does not exist")
        actor = rbac._actor(db, closed_by, target.organization_id, ("users.permissions.revoke",), today)
        user = rbac._user(db, user_id, actor.organization_id, today, require_active=False)
        rbac._protect_user(db, actor, user)
        rbac._permission(db, permission_id)
        record = rbac._current_assignment(db, UserPermission, user.organization_id, today,
                                          user_id=user.id, permission_id=permission_id)
        rbac._close(record, actor, reason, today)
        rbac._audit(db, actor, "user_permission.revoke", "user_permission", record,
                    before={"status": "open"}, after={"status": "closed", "reason": record.close_reason})
        return record
