"""Server-side default-deny rule governance. Caller must log every denied action."""
import os
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.models import User, RuleVersion, WrittenAuthorization

def has_permission(db: Session, user: User, code: str) -> bool:
    from mcias.services.authorization_service import check_permission_unified
    return check_permission_unified(db, user, code)

def can_edit_exclusion(db: Session, user: User) -> bool:
    return has_permission(db, user, "rules.exclusions.edit")

def can_activate_rule(db: Session, user: User, rule: RuleVersion) -> bool:
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
    from mcias.services.authorization_service import technical_identity
    if technical_identity(db,approver):
        return False
    if user.organization_id != rule.organization_id:
        return False
    if approval.approved_by == user.id:
        return False
    if os.getenv("MCIAS_ENVIRONMENT", "development") == "production":
        from mcias.production_authorization import verify_production_approval
        return verify_production_approval(db, rule, approval)
    return True
