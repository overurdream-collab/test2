import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, User, Role, UserRole, MFAFactor
from mcias.bootstrap_mfa import provision_privileged_factor

def test_offline_mfa_bootstrap_requires_privilege_and_is_one_time():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            user = User(username="synthetic-admin", password_hash="synthetic")
            db.add(user); db.commit()
            with pytest.raises(ValueError, match="super_admin"):
                provision_privileged_factor(db, user.username, os.urandom(32))
            role = Role(code="super_admin")
            db.add(role); db.flush()
            db.add(UserRole(user_id=user.id,role_id=role.id)); db.commit()
            secret = provision_privileged_factor(db, user.username, os.urandom(32))
            assert len(secret) == 32
            factor = db.get(MFAFactor, user.id)
            assert factor.enabled
            assert secret.encode() not in factor.encrypted_secret
            with pytest.raises(ValueError, match="already exists"):
                provision_privileged_factor(db, user.username, os.urandom(32))
    finally:
        engine.dispose()
