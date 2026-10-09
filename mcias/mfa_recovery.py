"""Offline dual-control recovery; the old MFA factor is replaced, never disabled."""
import base64
from cryptography.exceptions import InvalidSignature
import json
import os
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from mcias.models import User, MFAFactor, SessionToken, AuditLog

def verify_approvals(db, request, signatures, trusted_keys):
    payload = json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    subject = db.get(User, request["user_id"])
    if subject is None or not subject.active:
        raise ValueError("unknown subject")
    expiry = datetime.fromisoformat(request["expires_at"])
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise ValueError("expired request")
    if len(request["request_id"]) < 16 or len(request["evidence_sha256"]) != 64:
        raise ValueError("invalid evidence")
    if db.scalar(select(AuditLog.id).where(AuditLog.action == "mfa_recovered", AuditLog.resource_id == request["request_id"])):
        raise ValueError("replayed request")
    approved = set()
    for user_id, sig in signatures.items():
        signer = db.get(User, user_id)
        if signer is None or not signer.active or signer.id == subject.id or signer.organization_id != subject.organization_id:
            continue
        public_key = trusted_keys.get(user_id)
        if public_key is None:
            continue
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(bytes.fromhex(sig), payload)
            approved.add(user_id)
        except (ValueError, TypeError, InvalidSignature):
            pass
    if len(approved) < 2:
        raise ValueError("two independent trusted signatures required")
    return subject, sorted(approved)

def replace_factor(db, request, signatures, trusted_keys, key):
    if len(key) != 32:
        raise ValueError("invalid MFA encryption key")
    subject, approvers = verify_approvals(db, request, signatures, trusted_keys)
    # Serialize recovery for this subject on PostgreSQL to prevent concurrent requests.
    subject = db.scalar(select(User).where(User.id == subject.id).with_for_update())
    subject, approvers = verify_approvals(db, request, signatures, trusted_keys)
    import secrets
    secret = secrets.token_bytes(20)
    nonce = os.urandom(12)
    encrypted = nonce + AESGCM(key).encrypt(nonce, secret, subject.id.encode())
    factor = db.get(MFAFactor, subject.id)
    if factor is None:
        db.add(MFAFactor(user_id=subject.id, encrypted_secret=encrypted, enabled=True, last_accepted_counter=-1))
    else:
        factor.encrypted_secret = encrypted
        factor.enabled = True
        factor.last_accepted_counter = -1
    db.query(SessionToken).filter(SessionToken.user_id == subject.id, SessionToken.revoked_at.is_(None)).update({"revoked_at": datetime.now(timezone.utc)}, synchronize_session=False)
    db.add(AuditLog(actor_id=subject.id, action="mfa_recovered", resource_type="auth", resource_id=request["request_id"], details={"approvers": approvers, "evidence_sha256": request["evidence_sha256"]}))
    db.commit()
    return base64.b32encode(secret).decode().rstrip("=")
