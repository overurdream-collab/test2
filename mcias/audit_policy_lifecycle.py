"""G5 grant lifecycle: trusted administrators enroll signed grants; revocation is permanent."""
from datetime import datetime,timezone
from sqlalchemy import select
from mcias.models import User,AuditLog
from mcias.models_audit_policy import AuditPolicyGrant
from mcias.audit_authorization import verify_policy_authorization
from mcias.audit_engine import PolicyBlocked
from mcias.policy import has_permission

def enroll_grant(db, *, actor, organization_id, policy_id, policy_fingerprint,
                 approver_id, reviewer_id, signature):
    if (not actor.active or actor.organization_id!=organization_id or actor.id!=approver_id
        or not has_permission(db,actor,"policies.approve")):
        raise PolicyBlocked("policy approval permission required")
    approver=db.get(User,approver_id)
    reviewer=db.get(User,reviewer_id)
    if (approver is None or reviewer is None or not approver.active or not reviewer.active
        or approver.organization_id!=organization_id or reviewer.organization_id!=organization_id):
        raise PolicyBlocked("institutional signers invalid")
    try:
        verify_policy_authorization(organization_id=organization_id,
            policy_fingerprint=policy_fingerprint,approver_id=approver_id,
            reviewer_id=reviewer_id,signature=signature)
    except ValueError as exc:
        raise PolicyBlocked("institutional signature invalid") from exc
    if db.scalar(select(AuditPolicyGrant).where(AuditPolicyGrant.organization_id==organization_id,
        AuditPolicyGrant.policy_fingerprint==policy_fingerprint)) is not None:
        raise PolicyBlocked("policy fingerprint already registered; revoked approvals cannot be reused")
    grant=AuditPolicyGrant(organization_id=organization_id,policy_id=policy_id,
        policy_fingerprint=policy_fingerprint,approver_id=approver_id,
        reviewer_id=reviewer_id,signature=signature)
    db.add(grant)
    db.flush()
    db.add(AuditLog(actor_id=actor.id,action="policy_grant_enrolled",
        resource_type="audit_policy_grant",resource_id=grant.id,
        details={"organization_id":organization_id,"policy_fingerprint":policy_fingerprint}))
    db.commit()
    return grant

def revoke_grant(db, *, actor, grant_id):
    grant=db.scalar(select(AuditPolicyGrant).where(AuditPolicyGrant.id==grant_id).with_for_update())
    if grant is None or not actor.active or actor.organization_id!=grant.organization_id:
        raise PolicyBlocked("policy grant unavailable")
    if not has_permission(db,actor,"policies.revoke"):
        raise PolicyBlocked("policy revocation permission required")
    if grant.revoked_at is not None:
        raise PolicyBlocked("policy already revoked")
    grant.revoked_at=datetime.now(timezone.utc)
    db.add(AuditLog(actor_id=actor.id,action="policy_grant_revoked",
        resource_type="audit_policy_grant",resource_id=grant.id,
        details={"organization_id":grant.organization_id,"policy_fingerprint":grant.policy_fingerprint}))
    db.commit()
    return grant
