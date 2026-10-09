import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, Role, Permission, RolePermission, UserRole, AuditLog
from mcias.tenant import require_organization, require_sensitive_field

def test_tenant_and_medical_field_default_deny():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            a, b = Organization(name="tenant-A"), Organization(name="tenant-B")
            db.add_all([a,b]); db.flush()
            actor = User(username="tenant-reader", password_hash="synthetic", organization_id=a.id)
            role, perm = Role(code="tenant-reader-role"), Permission(code="claims.read")
            db.add_all([actor,role,perm]); db.flush()
            db.add_all([UserRole(user_id=actor.id,role_id=role.id), RolePermission(role_id=role.id,permission_id=perm.id)])
            db.commit()
            assert require_organization(db,actor,a.id,"claims.read")
            with pytest.raises(HTTPException) as err:
                require_organization(db,actor,b.id,"claims.read")
            assert err.value.status_code == 403
            with pytest.raises(HTTPException) as err:
                require_sensitive_field(db,actor,a.id,"diagnosis")
            assert err.value.status_code == 403
            assert db.query(AuditLog).filter_by(action="tenant_access_denied").count() == 2
    finally:
        engine.dispose()
