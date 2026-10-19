import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, Role, Permission, RolePermission, UserRole, AuditLog
from mcias.tenant import require_organization, require_sensitive_field
from mcias.denial_events import AuthorizationDenied

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
            # Guards express denial without committing the request transaction.
            # Durable two-event verification is mandatory in PostgreSQL/HTTP
            # tests/test_l2_audit_real_http_pg.py with the actual PR25 writer.
            assert db.query(AuditLog).filter_by(action="tenant_access_denied").count() == 0
            assert isinstance(err.value, AuthorizationDenied)
            # The two separate denials above must both be audited by the
            # request owner; verify their metadata explicitly below.
            with pytest.raises(AuthorizationDenied) as tenant_denied:
                require_organization(db, actor, b.id, "claims.read")
            with pytest.raises(AuthorizationDenied) as sensitive_denied:
                require_sensitive_field(db, actor, a.id, "diagnosis")
            assert tenant_denied.value.audit_action == "tenant_access_denied"
            assert tenant_denied.value.audit_resource_id == b.id
            assert sensitive_denied.value.audit_action == "tenant_access_denied"
            assert sensitive_denied.value.audit_resource_id == a.id
            assert tenant_denied.value.audit_actor_id == sensitive_denied.value.audit_actor_id == actor.id
            assert tenant_denied.value.audit_organization_id == sensitive_denied.value.audit_organization_id == a.id
            # No event may be persisted by a guard on the business Session.
            assert db.query(AuditLog).filter_by(action="tenant_access_denied").count() == 0
    finally:
        engine.dispose()
