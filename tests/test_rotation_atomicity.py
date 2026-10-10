import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, User, MFAFactor
from mcias.mfa_key_rotation import rotate_all_factors

def test_corrupt_factor_prevents_rotation():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(username="bad-factor", password_hash="synthetic")
        db.add(user)
        db.flush()
        db.add(MFAFactor(user_id=user.id, encrypted_secret=b"bad", enabled=True))
        db.commit()
        with pytest.raises(ValueError):
            rotate_all_factors(db, os.urandom(32), os.urandom(32))
        assert db.get(MFAFactor, user.id).encrypted_secret == b"bad"
    engine.dispose()
