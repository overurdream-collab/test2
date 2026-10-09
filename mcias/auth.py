"""Database-backed session authentication."""
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.models import User, SessionToken, AuditLog
from mcias.security import verify_password, new_session_token, session_not_expired
from mcias.policy import has_permission

def authenticate(db: Session, username: str, password: str):
    user = db.scalar(select(User).where(User.username == username, User.active.is_(True)))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
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
    if user is None or not user.active:
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
