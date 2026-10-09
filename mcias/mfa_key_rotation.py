"""Offline MFA key rotation primitive; operator approval and custody are external."""
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def rewrap_mfa_secret(envelope: bytes, user_id: str, old_key: bytes, new_key: bytes) -> bytes:
    if len(old_key) != 32 or len(new_key) != 32:
        raise ValueError("AES-256 keys required")
    if len(envelope) < 29 or not user_id:
        raise ValueError("invalid MFA envelope")
    secret = AESGCM(old_key).decrypt(envelope[:12], envelope[12:], user_id.encode())
    if len(secret) != 20:
        raise ValueError("invalid TOTP secret length")
    nonce = os.urandom(12)
    return nonce + AESGCM(new_key).encrypt(nonce, secret, user_id.encode())


def rotate_all_factors(db, old_key: bytes, new_key: bytes) -> int:
    """Offline atomic rewrap. Caller MUST back up and retain old key until restore verified."""
    from sqlalchemy import select
    from mcias.models import MFAFactor, AuditLog
    factors = db.scalars(select(MFAFactor).with_for_update()).all()
    try:
        rotated = [(factor, rewrap_mfa_secret(factor.encrypted_secret, factor.user_id, old_key, new_key)) for factor in factors]
        for factor, envelope in rotated:
            factor.encrypted_secret = envelope
        db.add(AuditLog(action="offline_mfa_key_rotation", resource_type="auth", details={"factors": len(rotated)}))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(rotated)
