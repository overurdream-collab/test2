import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User
from mcias.tenant import require_organization

def test_inactive_user_denied_even_for_same_tenant():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org=Organization(name="fixture")
        db.add(org); db.flush()
        user=User(username="disabled",password_hash="fixture",organization_id=org.id,active=False)
        db.add(user); db.commit()
        with pytest.raises(HTTPException) as error:
            require_organization(db,user,org.id,"claims.read")
        assert error.value.status_code == 403
    engine.dispose()
