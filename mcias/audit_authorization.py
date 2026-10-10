"""Server-side HMAC authorization for G5 financial policies.

Signatures are issued by an institutional approval workflow, not an API caller.
The signing secret stays on-premises and must not be committed to source control.
"""
from dataclasses import dataclass
import hashlib
import hmac
import os

@dataclass(frozen=True)
class VerifiedPolicyAuthorization:
    organization_id: str
    policy_fingerprint: str
    signature_verified: bool
    independent_reviewer_verified: bool

def verify_policy_authorization(*, organization_id, policy_fingerprint,
                                approver_id, reviewer_id, signature):
    if not organization_id or not policy_fingerprint or not approver_id or not reviewer_id:
        raise ValueError("incomplete policy approval")
    if approver_id==reviewer_id:
        raise ValueError("independent reviewer required")
    secret=os.environ.get("MCIAS_G5_POLICY_VERIFICATION_KEY","")
    if len(secret)<32:
        raise ValueError("institutional verification key unavailable")
    message="|".join((organization_id,policy_fingerprint,approver_id,reviewer_id)).encode()
    expected=hmac.new(secret.encode(),message,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature):
        raise ValueError("invalid policy signature")
    return VerifiedPolicyAuthorization(organization_id,policy_fingerprint,True,True)
