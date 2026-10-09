"""Server-side default-deny rule governance. Caller must log every denied action."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.models import User, Permission, RolePermission, UserRole, RuleVersion, WrittenAuthorization

def has_permission(db: Session, user: User, code: str) -> bool:
    if not user.active:
        return False
    query = select(Permission.id).join(RolePermission, RolePermission.permission_id == Permission.id).join(UserRole, UserRole.role_id == RolePermission.role_id).where(UserRole.user_id == user.id, Permission.code == code)
    return db.scalar(query) is not None

def can_edit_exclusion(db: Session, user: User) -> bool:
    return has_permission(db, user, "rules.exclusions.edit")

def can_activate_rule(db: Session, user: User, rule: RuleVersion) -> bool:
    if rule.status != "draft" or not has_permission(db, user, "rules.activate") or not rule.written_authorization_id:
        return False
    approval = db.get(WrittenAuthorization, rule.written_authorization_id)
    return bool(approval and approval.organization_id == rule.organization_id and approval.source_id and approval.approved_by)
