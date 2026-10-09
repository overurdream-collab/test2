from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, User, SessionToken
from mcias.security import hash_password, new_session_token
from mcias.auth import resolve_user, revoke_session

def test_session_expiry_revocation_and_inactive_user():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            user = User(username="session-test", password_hash=hash_password("synthetic-long-password"))
            db.add(user); db.flush()
            token, token_hash = new_session_token()
            row = SessionToken(user_id=user.id, token_hash=token_hash, expires_at=datetime.now(timezone.utc)+timedelta(minutes=10))
            db.add(row); db.commit()
            assert resolve_user(db, "Bearer " + token)[0].id == user.id
            for bad in (None, "Bearer ", "Basic " + token, "Bearer " + "x"*300):
                with pytest.raises(HTTPException) as exc:
                    resolve_user(db, bad)
                assert exc.value.status_code == 401
            revoke_session(db, row)
            with pytest.raises(HTTPException):
                resolve_user(db, "Bearer " + token)
            row.revoked_at = None
            row.expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
            db.commit()
            with pytest.raises(HTTPException):
                resolve_user(db, "Bearer " + token)
            row.expires_at = datetime.now(timezone.utc)+timedelta(minutes=10)
            user.active = False
            db.commit()
            with pytest.raises(HTTPException):
                resolve_user(db, "Bearer " + token)
    finally:
        engine.dispose()
