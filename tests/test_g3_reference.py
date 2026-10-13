from tests.authorization_fixtures import approve_fixture
"""G3 synthetic temporal contract acceptance tests."""
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, SourceFile, WrittenAuthorization, AuditLog
from mcias.models_reference import ContractVersion, ProviderTariff, BeneficiaryCategory, BeneficiaryEnrollment
from mcias.reference import ReferenceConflict, overlaps, check_contract_overlap, analyze_retroactive, approve_contract, active_contract

def test_half_open_ranges():
    assert not overlaps(date(2026,1,1),date(2026,2,1),date(2026,2,1),date(2026,3,1))
    assert overlaps(date(2026,1,1),date(2026,2,2),date(2026,2,1),date(2026,3,1))
    with pytest.raises(ReferenceConflict):
        overlaps(date(2026,2,1),date(2026,1,1),date(2026,2,1),date(2026,3,1))

def test_t04_t05_conflicts_and_retroactivity():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org=Organization(name="synthetic")
        db.add(org);db.flush()
        old=ContractVersion(organization_id=org.id,provider_code="H1",version=1,
            effective_from=date(2026,1,1),effective_until=date(2026,6,1),status="approved",precedence=1)
        proposal=ContractVersion(organization_id=org.id,provider_code="H1",version=2,
            effective_from=date(2026,5,1),effective_until=date(2026,12,1),status="draft",precedence=1)
        db.add_all([old,proposal]);db.commit()
        with pytest.raises(ReferenceConflict,match="T04"):
            check_contract_overlap(db,proposal)
        impact=analyze_retroactive(db,proposal,date(2026,10,10))
        assert impact["retroactive"]
        assert old.id in impact["conflicting_contract_ids"]
        assert impact["requires_human_review"]
        assert active_contract(db,org.id,"H1",date(2026,2,1)).id==old.id
        assert active_contract(db,org.id,"H1",date(2026,6,1)) is None
    engine.dispose()

def test_unapproved_precedence_or_missing_authorization_blocks_activation():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org=Organization(name="synthetic")
        user=User(username="actor",password_hash="fixture")
        db.add_all([org,user]);db.flush()
        user.organization_id=org.id
        proposal=ContractVersion(organization_id=org.id,provider_code="H1",version=1,
            effective_from=date(2027,1,1),effective_until=date(2028,1,1),status="draft")
        db.add(proposal);db.flush()
        from mcias.models import Role,Permission,UserRole,RolePermission
        role=Role(code='SYN-contract-check');permission=Permission(code='reference.approve')
        db.add_all([role,permission]);db.flush()
        db.add_all([UserRole(user_id=user.id,role_id=role.id),RolePermission(role_id=role.id,permission_id=permission.id)])
        db.flush();approve_fixture(db,org.id);db.commit()
        with pytest.raises(ReferenceConflict,match="precedence"):
            approve_contract(db,proposal.id,user,date(2026,10,10))
        with pytest.raises(ReferenceConflict,match="written authorization"):
            approve_contract(db,proposal.id,user,date(2026,10,10),precedence_approved=True)
        assert db.get(ContractVersion,proposal.id).status=="draft"
    engine.dispose()

def test_approved_contract_immutable():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org=Organization(name="synthetic")
        db.add(org);db.flush()
        contract=ContractVersion(organization_id=org.id,provider_code="H1",version=1,
            effective_from=date(2026,1,1),effective_until=date(2027,1,1),status="approved")
        db.add(contract);db.commit()
        contract.effective_until=date(2028,1,1)
        with pytest.raises(ValueError,match="immutable"):
            db.commit()
        db.rollback()
    engine.dispose()

def test_beneficiary_temporal_conflict_and_tenant_category():
    from mcias.reference import validate_enrollment
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org1=Organization(name="org1")
        org2=Organization(name="org2")
        db.add_all([org1,org2]);db.flush()
        category=BeneficiaryCategory(organization_id=org1.id,code="A",description="synthetic")
        db.add(category);db.flush()
        current=BeneficiaryEnrollment(organization_id=org1.id,beneficiary_token="opaque-token",
            category_id=category.id,effective_from=date(2026,1,1),effective_until=date(2026,12,1))
        db.add(current);db.commit()
        overlap=BeneficiaryEnrollment(organization_id=org1.id,beneficiary_token="opaque-token",
            category_id=category.id,effective_from=date(2026,6,1),effective_until=date(2027,1,1))
        with pytest.raises(ReferenceConflict,match="overlapping"):
            validate_enrollment(db,overlap)
        wrong_tenant=BeneficiaryEnrollment(organization_id=org2.id,beneficiary_token="opaque-token",
            category_id=category.id,effective_from=date(2027,1,1),effective_until=date(2028,1,1))
        with pytest.raises(ReferenceConflict,match="same organization"):
            validate_enrollment(db,wrong_tenant)
    engine.dispose()
