"""Default-deny tenant and sensitive-field access guards."""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from mcias.models import AuditLog, User
from mcias.policy import has_permission

def require_organization(db: Session, actor: User, organization_id: str, permission: str):
    if not actor.active or not actor.organization_id or actor.organization_id != organization_id or not has_permission(db, actor, permission):
        from mcias.denial_events import AuthorizationDenied
        raise AuthorizationDenied(actor_id=actor.id, organization_id=actor.organization_id,
                                  action="tenant_access_denied", resource_type="organization",
                                  resource_id=organization_id, reason_code="tenant_or_permission_denied")
    return True

def require_sensitive_field(db: Session, actor: User, organization_id: str, field_code: str):
    if not field_code or not field_code.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="invalid field")
    return require_organization(db, actor, organization_id, "medical_fields." + field_code + ".read")
