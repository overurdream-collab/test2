"""Audited rule governance: never activate without independent written authorization."""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from mcias.models import AuditLog, RuleVersion, User
from mcias.policy import can_activate_rule, can_edit_exclusion, has_permission

def deny(db: Session, user: User, action: str, rule_id: str):
    db.add(AuditLog(actor_id=user.id, action="governance_denied", resource_type="rule", resource_id=rule_id, details={"attempted_action": action}))
    db.commit()
    raise HTTPException(status_code=403, detail="forbidden")

def activate_rule(db: Session, user: User, rule_id: str):
    rule = db.get(RuleVersion, rule_id, with_for_update=True)
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    if not can_activate_rule(db, user, rule):
        deny(db, user, "activate", rule_id)
    rule.status = "active"
    db.add(AuditLog(actor_id=user.id, action="rule_activated", resource_type="rule", resource_id=rule_id, details={"authorization_id": rule.written_authorization_id}))
    db.commit()
    return {"id": rule.id, "status": rule.status}

def exclusion_edit_permission(db: Session, user: User):
    if not can_edit_exclusion(db, user):
        deny(db, user, "edit_exclusion", "none")
    return {"allowed": True}
