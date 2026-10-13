"""Database-backed session authentication."""
import hashlib
from mcias.login_limits import blocked, record_failure, clear_failures
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.models import User, SessionToken, AuditLog, MFAFactor, Role, UserRole
from mcias.mfa import verify_totp
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import os
from mcias.security import verify_password, new_session_token, session_not_expired
from mcias.policy import has_permission
from mcias.services.authorization_service import live_user

def authenticate(db: Session, username: str, password: str, totp_code: str | None = None):
    identity_hash = hashlib.sha256(username.strip().casefold().encode()).hexdigest()
    if blocked(db, identity_hash):
        raise HTTPException(status_code=429, detail="login temporarily restricted")
    user = db.scalar(select(User).where(User.username == username, User.active.is_(True)))
    if not live_user(user) or not verify_password(password, user.password_hash):
        record_failure(db, identity_hash)
        raise HTTPException(status_code=401, detail="invalid credentials")
    privileged = db.scalar(select(Role.id).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id, Role.code == "super_admin")) is not None
    factor = db.scalar(select(MFAFactor).where(MFAFactor.user_id == user.id).with_for_update())
    if privileged or (factor is not None and factor.enabled):
        if factor is None or not factor.enabled or not totp_code:
            record_failure(db, identity_hash)
            raise HTTPException(status_code=401, detail="MFA required")
        try:
            key = bytes.fromhex(os.environ["MCIAS_MFA_ENCRYPTION_KEY"])
            if len(key) != 32:
                raise ValueError("invalid MFA key")
            nonce, ciphertext = factor.encrypted_secret[:12], factor.encrypted_secret[12:]
            secret = AESGCM(key).decrypt(nonce, ciphertext, user.id.encode())
            counter = verify_totp(secret, totp_code, factor.last_accepted_counter)
        except (KeyError, ValueError, InvalidTag):
            raise HTTPException(status_code=503, detail="MFA unavailable")
        if counter is None:
            record_failure(db, identity_hash)
            raise HTTPException(status_code=401, detail="invalid MFA code")
        factor.last_accepted_counter = counter
    clear_failures(db, identity_hash)
    token, token_hash = new_session_token()
    db.add(SessionToken(user_id=user.id, token_hash=token_hash, expires_at=datetime.now(timezone.utc)+timedelta(minutes=30)))
    db.add(AuditLog(actor_id=user.id, action="login", resource_type="auth"))
    db.commit()
    return token

def resolve_user(db: Session, authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    token = authorization[7:]
    if not token or len(token) > 256:
        raise HTTPException(status_code=401, detail="invalid session")
    session = db.scalar(select(SessionToken).where(SessionToken.token_hash == hashlib.sha256(token.encode()).hexdigest()))
    if session is None or session.revoked_at is not None or not session_not_expired(session.expires_at):
        raise HTTPException(status_code=401, detail="invalid session")
    user = db.get(User, session.user_id)
    if not live_user(user):
        raise HTTPException(status_code=401, detail="invalid session")
    return user, session

def require_permission(db: Session, user: User, permission: str):
    if not has_permission(db, user, permission):
        db.add(AuditLog(actor_id=user.id, action="permission_denied", resource_type="permission", details={"permission": permission}))
        db.commit()
        raise HTTPException(status_code=403, detail="forbidden")

def revoke_session(db: Session, session: SessionToken):
    session.revoked_at = datetime.now(timezone.utc)
    db.add(AuditLog(actor_id=session.user_id, action="logout", resource_type="auth"))
    db.commit()
