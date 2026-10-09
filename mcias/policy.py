"""Server-side default-deny rule governance. Caller must log every denied action."""
import os
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
    # Production activation stays closed until signed authorization verification ships.
    if os.getenv("MCIAS_ENVIRONMENT", "development") == "production":
        return False
    if rule.status != "draft" or not has_permission(db, user, "rules.activate") or not rule.written_authorization_id:
        return False
    approval = db.get(WrittenAuthorization, rule.written_authorization_id)
    if not approval or approval.organization_id != rule.organization_id or not approval.source_id or not approval.approved_by:
        return False
    # A recorded authorization is not proof of an organization's head signature.
    # Require a distinct, active approver in the same organization; external
    # signature verification remains an explicit production acceptance blocker.
    approver = db.get(User, approval.approved_by)
    if not approver or not approver.active or approver.organization_id != rule.organization_id:
        return False
    if user.organization_id != rule.organization_id:
        return False
    return approval.approved_by != user.id
