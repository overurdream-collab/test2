"""Two-stage MFA enrollment. Never log or persist the plaintext secret."""
import os
import secrets
import time
from fastapi import HTTPException
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.models import MFAFactor, AuditLog, User, SessionToken
from mcias.mfa import verify_totp

def encryption_key():
    try:
        key = bytes.fromhex(os.environ["MCIAS_MFA_ENCRYPTION_KEY"])
        if len(key) != 32:
            raise ValueError("invalid key")
        return key
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="MFA unavailable") from exc

def begin_enrollment(db: Session, user: User):
    factor = db.scalar(select(MFAFactor).where(MFAFactor.user_id == user.id).with_for_update())
    if factor is not None and factor.enabled:
        raise HTTPException(status_code=409, detail="MFA already enabled")
    secret = secrets.token_bytes(20)
    nonce = os.urandom(12)
    encrypted = nonce + AESGCM(encryption_key()).encrypt(nonce, secret, user.id.encode())
    if factor is None:
        factor = MFAFactor(user_id=user.id, encrypted_secret=encrypted, enabled=False, last_accepted_counter=-1)
        db.add(factor)
    else:
        factor.encrypted_secret = encrypted
        factor.last_accepted_counter = -1
    db.add(AuditLog(actor_id=user.id, action="mfa_enrollment_started", resource_type="auth"))
    db.commit()
    import base64
    return {"secret_base32": base64.b32encode(secret).decode().rstrip("="), "algorithm": "SHA1", "digits": 6, "period": 30}

def confirm_enrollment(db: Session, user: User, code: str):
    factor = db.scalar(select(MFAFactor).where(MFAFactor.user_id == user.id).with_for_update())
    if factor is None or factor.enabled:
        raise HTTPException(status_code=409, detail="MFA enrollment not pending")
    try:
        nonce, ciphertext = factor.encrypted_secret[:12], factor.encrypted_secret[12:]
        secret = AESGCM(encryption_key()).decrypt(nonce, ciphertext, user.id.encode())
    except (InvalidTag, ValueError) as exc:
        raise HTTPException(status_code=503, detail="MFA unavailable") from exc
    counter = verify_totp(secret, code, now=int(time.time()))
    if counter is None:
        raise HTTPException(status_code=401, detail="invalid MFA code")
    factor.enabled = True
    factor.last_accepted_counter = counter
    # Revoke all sessions issued before MFA activation.
    from datetime import datetime, timezone
    db.query(SessionToken).filter(
        SessionToken.user_id == user.id,
        SessionToken.revoked_at.is_(None),
    ).update({"revoked_at": datetime.now(timezone.utc)}, synchronize_session=False)
    db.add(AuditLog(actor_id=user.id, action="mfa_enabled", resource_type="auth"))
    db.commit()
    return {"enabled": True}
