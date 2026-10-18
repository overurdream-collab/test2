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
