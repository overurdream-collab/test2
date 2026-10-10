import os
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, User, MFAFactor
from mcias.security import hash_password
from mcias.auth import authenticate

def test_corrupted_mfa_ciphertext_fails_closed(monkeypatch):
    monkeypatch.setenv("MCIAS_MFA_ENCRYPTION_KEY", "11" * 32)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            user = User(username="tampered", password_hash=hash_password("synthetic-long-password"))
            db.add(user)
            db.flush()
            db.add(MFAFactor(user_id=user.id, encrypted_secret=b"broken-ciphertext", enabled=True))
            db.commit()
            with pytest.raises(HTTPException) as exc:
                authenticate(db, "tampered", "synthetic-long-password", "123456")
            assert exc.value.status_code == 503
            assert db.query(__import__("mcias.models", fromlist=["SessionToken"]).SessionToken).count() == 0
            monkeypatch.delenv("MCIAS_MFA_ENCRYPTION_KEY")
            with pytest.raises(HTTPException) as exc:
                authenticate(db, "tampered", "synthetic-long-password", "123456")
            assert exc.value.status_code == 503
    finally:
        engine.dispose()
