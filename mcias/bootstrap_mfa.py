"""Offline one-time bootstrap of privileged MFA; requires secured console access."""
import base64
import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from mcias.models import User, Role, UserRole, MFAFactor, AuditLog

def provision_privileged_factor(db: Session, username: str, key: bytes) -> str:
    if len(key) != 32:
        raise ValueError("AES-256 key required")
    user = db.scalar(select(User).where(User.username == username, User.active.is_(True)).with_for_update())
    if user is None:
        raise ValueError("active user required")
    is_admin = db.scalar(select(Role.id).join(UserRole, Role.id == UserRole.role_id).where(UserRole.user_id == user.id, Role.code == "super_admin"))
    if is_admin is None:
        raise ValueError("super_admin role required")
    existing = db.scalar(select(MFAFactor).where(MFAFactor.user_id == user.id).with_for_update())
    if existing is not None:
        raise ValueError("MFA factor already exists; recovery procedure required")
    secret = secrets.token_bytes(20)
    nonce = os.urandom(12)
    db.add(MFAFactor(user_id=user.id, encrypted_secret=nonce + AESGCM(key).encrypt(nonce, secret, user.id.encode()), enabled=True, last_accepted_counter=-1))
    db.add(AuditLog(actor_id=user.id, action="offline_mfa_bootstrap", resource_type="auth"))
    db.commit()
    return base64.b32encode(secret).decode().rstrip("=")

def main():
    import argparse
    import getpass
    parser = argparse.ArgumentParser(description="Local-console privileged MFA bootstrap")
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    key = bytes.fromhex(os.environ["MCIAS_MFA_ENCRYPTION_KEY"])
    engine = create_engine(os.environ["MCIAS_DATABASE_URL"])
    try:
        with Session(engine) as db:
            secret = provision_privileged_factor(db, args.username, key)
            print("Provision this one-time TOTP secret in an approved authenticator; do not store it:")
            print(secret)
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
