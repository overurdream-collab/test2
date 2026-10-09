from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import HTTPException
import pytest
from mcias.models import Base, User
from mcias.auth import authenticate
from mcias.security import hash_password

def test_repeated_failures_are_throttled():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(username="synthetic-user", password_hash=hash_password("long-synthetic-password")))
        db.commit()
        for attempt in range(5):
            with pytest.raises(HTTPException) as error:
                authenticate(db, "synthetic-user", "invalid")
            assert error.value.status_code == 401
        with pytest.raises(HTTPException) as error:
            authenticate(db, "synthetic-user", "long-synthetic-password")
        assert error.value.status_code == 429
    engine.dispose()
