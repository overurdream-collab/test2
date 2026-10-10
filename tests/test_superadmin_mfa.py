import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, User, Role, UserRole
from mcias.security import hash_password
from mcias.auth import authenticate

def test_super_admin_without_mfa_enrollment_cannot_login():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(username="privileged", password_hash=hash_password("long-synthetic-password"))
        role = Role(code="super_admin")
        db.add_all([user, role])
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        with pytest.raises(HTTPException) as exc:
            authenticate(db, "privileged", "long-synthetic-password")
        assert exc.value.status_code == 401
    engine.dispose()
