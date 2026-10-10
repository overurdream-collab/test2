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
        db.add(proposal);db.commit()
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
