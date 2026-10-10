from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from mcias.models import Base, User, Role, Permission, UserRole, RolePermission, Organization, SourceFile, Claim, RuleVersion, WrittenAuthorization, AuditLog
from mcias.policy import can_edit_exclusion, can_activate_rule

@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    @event.listens_for(engine, "connect")
    def fk(conn, record):
        conn.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def setup(db):
    org = Organization(name="Synthetic Insurer")
    user = User(username="test-user", password_hash="test-only")
    source = SourceFile(sha256="a"*64, original_filename="synthetic.xlsx", storage_key="encrypted")
    db.add_all([org, user, source]); db.flush()
    user.organization_id = org.id
    db.flush()
    return org, user, source

def test_t06_exclusion_edit_default_deny(db):
    org, user, source = setup(db)
    assert not can_edit_exclusion(db, user)

def test_t07_activation_requires_written_authorization(db):
    org, user, source = setup(db)
    role = Role(code="super_admin")
    permission = Permission(code="rules.activate")
    db.add_all([role, permission]); db.flush()
    db.add_all([UserRole(user_id=user.id, role_id=role.id), RolePermission(role_id=role.id, permission_id=permission.id)])
    rule = RuleVersion(organization_id=org.id, rule_type="exclusion")
    db.add(rule); db.flush()
    assert not can_activate_rule(db, user, rule)
    approval = WrittenAuthorization(organization_id=org.id, source_id=source.id, approved_by=user.id, approved_at=datetime.now(timezone.utc))
    db.add(approval); db.flush()
    rule.written_authorization_id = approval.id
    assert not can_activate_rule(db, user, rule)  # self-authorization forbidden
    approver = User(username="org-head-test", password_hash="test-only", organization_id=org.id)
    db.add(approver); db.flush()
    approval.approved_by = approver.id
    assert can_activate_rule(db, user, rule)
    approver.active = False
    db.flush()
    assert not can_activate_rule(db, user, rule)

def test_t11_approved_claim_immutable(db):
    org, user, source = setup(db)
    claim = Claim(source_id=source.id, original_payload={"row":1}, original_claimed_amount=Decimal("20.00"), currency="YER", status="approved")
    db.add(claim); db.commit()
    claim.original_claimed_amount = Decimal("30.00")
    with pytest.raises(ValueError, match="approved claim"):
        db.flush()

def test_original_amount_immutable_before_approval(db):
    org, user, source = setup(db)
    claim = Claim(source_id=source.id, original_payload={"row":1}, original_claimed_amount=Decimal("20.00"), currency="YER")
    db.add(claim); db.commit()
    claim.original_claimed_amount = Decimal("30.00")
    with pytest.raises(ValueError, match="immutable"):
        db.flush()

def test_audit_log_append_only_orm(db):
    org, user, source = setup(db)
    log = AuditLog(action="created", resource_type="claim")
    db.add(log); db.commit()
    log.action = "changed"
    with pytest.raises(ValueError, match="append-only"):
        db.flush()


def test_production_rule_activation_fails_closed(db, monkeypatch):
    org, user, source = setup(db)
    rule = RuleVersion(organization_id=org.id, rule_type="exclusion")
    db.add(rule)
    db.flush()
    monkeypatch.setenv("MCIAS_ENVIRONMENT", "production")
    assert not can_activate_rule(db, user, rule)
