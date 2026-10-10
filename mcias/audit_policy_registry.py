"""Tenant-aware policy grant checks; fail closed for revoked or invalid grants."""
from sqlalchemy import select
from mcias.audit_authorization import verify_policy_authorization
from mcias.models_audit_policy import AuditPolicyGrant
from mcias.models import User
from mcias.audit_engine import PolicyBlocked
from mcias.policy import has_permission

def resolve_grant(db, *, organization_id, policy_fingerprint, policy_id):
    grant=db.scalar(select(AuditPolicyGrant).where(
        AuditPolicyGrant.organization_id==organization_id,
        AuditPolicyGrant.policy_fingerprint==policy_fingerprint,
        AuditPolicyGrant.policy_id==policy_id))
    if grant is None or grant.revoked_at is not None:
        raise PolicyBlocked("active institutional policy grant required")
    approver=db.get(User,grant.approver_id)
    reviewer=db.get(User,grant.reviewer_id)
    if (approver is None or reviewer is None or not approver.active or not reviewer.active
        or approver.id==reviewer.id or approver.organization_id!=organization_id
        or reviewer.organization_id!=organization_id):
        raise PolicyBlocked("institutional signers invalid")
    if not has_permission(db,approver,"policies.approve") or not has_permission(db,reviewer,"policies.review"):
        raise PolicyBlocked("institutional signer permission revoked")
    try:
        return verify_policy_authorization(
            organization_id=organization_id,policy_fingerprint=policy_fingerprint,
            approver_id=approver.id,reviewer_id=reviewer.id,signature=grant.signature)
    except ValueError as exc:
        raise PolicyBlocked("policy signature verification failed") from exc
