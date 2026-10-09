"""Offline recovery. Trusted signing keys and identity proof require external governance."""
import json
from datetime import datetime, timezone
from fastapi import HTTPException
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import select
from mcias.models import AuditLog, User, MFAFactor, SessionToken

def execute_recovery(db, request, signatures, trusted_keys):
    subject = db.get(User, request.get("user_id"))
    if subject is None or not subject.active:
        raise ValueError("invalid subject")
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or len(request_id) < 16:
        raise ValueError("invalid recovery request")
    expiry = datetime.fromisoformat(request["expires_at"])
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise ValueError("expired recovery request")
    if request.get("identity_verified") is not True or not request.get("evidence_sha256"):
        raise ValueError("independent identity evidence required")
    if db.scalar(select(AuditLog.id).where(AuditLog.action == "mfa_recovered", AuditLog.resource_id == request_id)):
        raise ValueError("recovery replay")
    payload = json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    valid = set()
    for approver_id, signature in signatures.items():
        approver = db.get(User, approver_id)
        if approver is None or not approver.active or approver.id == subject.id or approver_id not in trusted_keys:
            continue
        try:
            Ed25519PublicKey.from_public_bytes(trusted_keys[approver_id]).verify(bytes.fromhex(signature), payload)
            valid.add(approver_id)
        except (ValueError, TypeError):
            continue
        except Exception:
            continue
    if len(valid) < 2:
        raise ValueError("two distinct valid authorized signatures required")
    factor = db.get(MFAFactor, subject.id)
    if factor is not None:
        db.delete(factor)
    from datetime import datetime as dt
    db.query(SessionToken).filter(SessionToken.user_id == subject.id, SessionToken.revoked_at.is_(None)).update({"revoked_at": dt.now(timezone.utc)}, synchronize_session=False)
    db.add(AuditLog(action="mfa_recovered", actor_id=subject.id, resource_type="auth", resource_id=request_id, details={"approvers": sorted(valid), "evidence_sha256": request["evidence_sha256"]}))
    db.commit()
    return {"recovered": True, "sessions_revoked": True, "requires_new_mfa": True}
