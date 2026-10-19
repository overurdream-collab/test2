"""Authorization denial metadata. Persistence is handled by the request transaction owner.

Requires the shared mcias.audit_writer from PR #25 at integration time.
"""
from fastapi import HTTPException


class AuthorizationDenied(HTTPException):
    def __init__(self, *, actor_id, organization_id, action, resource_type, resource_id=None, reason_code="permission_denied"):
        super().__init__(status_code=403, detail="forbidden")
        self.audit_actor_id = actor_id
        self.audit_organization_id = organization_id
        self.audit_action = action
        self.audit_resource_type = resource_type
        self.audit_resource_id = resource_id
        self.audit_reason_code = reason_code

def record_denial_after_rollback(bind, denied):
    """Delegate to PR #25 shared writer ONLY; never commit the business session.

    Integration cannot pass until the separately owned shared writer is available.
    """
    if not denied.audit_actor_id or not denied.audit_organization_id:
        # Anonymous authentication failures require a distinct security-event contract.
        raise RuntimeError("authenticated audit identity required; anonymous audit contract pending")
    from mcias.audit_writer import record_outcome_independent
    return record_outcome_independent(
        bind, actor_id=denied.audit_actor_id,
        organization_id=denied.audit_organization_id,
        action=denied.audit_action, resource_type=denied.audit_resource_type,
        resource_id=denied.audit_resource_id, outcome="denied",
        details={"reason_code": denied.audit_reason_code})
