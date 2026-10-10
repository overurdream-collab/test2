"""G3 lifecycle acceptance: authorization, tariffs, eligibility, audit and approval."""
from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, SourceFile, WrittenAuthorization, AuditLog
from mcias.models_reference import ContractVersion, ProviderTariff
from mcias.reference import ReferenceConflict, approve_contract
from mcias.reference_service import (create_draft, add_tariff, create_category, enroll, eligibility,
    attach_authorization, impact_review, approve_precedence_policy)

@pytest.fixture
def db():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()

def setup_actors(db):
    org=Organization(name="synthetic")
    actors=[User(username="g3-"+str(i),password_hash="synthetic") for i in range(4)]
    db.add(org);db.add_all(actors);db.flush()
    for actor in actors:
        actor.organization_id=org.id
    source=SourceFile(sha256="f"*64,original_filename="authorization.pdf",storage_key="g3-synthetic-authorization")
    db.add(source);db.flush()
    authorization=WrittenAuthorization(organization_id=org.id,source_id=source.id,
        approved_by=actors[0].id,approved_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    db.add(authorization);db.commit()
    return org,actors,authorization

def test_full_authorized_reference_lifecycle(db):
    org,actors,auth=setup_actors(db)
    writer,reviewer,precedence,activator=actors
    contract=create_draft(db,writer,"HOSP-A",date(2027,1,1),date(2028,1,1))
    assert contract.version==1
    tariff=add_tariff(db,writer,contract.id,"CONSULT",Decimal("123.4500"),"YER")
    assert tariff.amount==Decimal("123.4500")
    with pytest.raises(ReferenceConflict,match="duplicate"):
        add_tariff(db,writer,contract.id,"CONSULT",Decimal("1"),"YER")
    attach_authorization(db,reviewer,contract.id,auth.id)
    with pytest.raises(ReferenceConflict,match="precedence"):
        approve_contract(db,contract.id,activator,date(2026,10,10),precedence_approved=True)
    approve_precedence_policy(db,precedence,contract.id,"Hospital specific tariff precedence approved in signed reference policy")
    assert approve_contract(db,contract.id,activator,date(2026,10,10),precedence_approved=True)["status"]=="approved"
    with pytest.raises(ReferenceConflict,match="immutable"):
        add_tariff(db,writer,contract.id,"NEW",Decimal("1"),"YER")
    assert db.scalar(select(AuditLog.id).where(AuditLog.action=="contract_approved")) is not None

def test_retroactive_requires_independent_review(db):
    org,actors,auth=setup_actors(db)
    writer,reviewer,precedence,activator=actors
    contract=create_draft(db,writer,"HOSP-B",date(2026,1,1),date(2027,1,1))
    attach_authorization(db,reviewer,contract.id,auth.id)
    approve_precedence_policy(db,precedence,contract.id,"Documented precedence rule for historical service dates")
    with pytest.raises(ReferenceConflict,match="retroactive"):
        approve_contract(db,contract.id,activator,date(2026,10,10),precedence_approved=True)
    impact=impact_review(db,reviewer,contract.id,"Reviewed all affected service dates and no financial amount was auto-adjusted",date(2026,10,10))
    assert impact["requires_human_review"]
    assert approve_contract(db,contract.id,activator,date(2026,10,10),precedence_approved=True)["status"]=="approved"

def test_beneficiary_eligibility_and_conflict(db):
    org,actors,_=setup_actors(db)
    category=create_category(db,actors[1],"A","Synthetic category")
    enroll(db,actors[1],"opaque-synthetic-token",category.id,date(2026,1,1),date(2026,12,1))
    assert eligibility(db,org.id,"opaque-synthetic-token",date(2026,6,1)).category_id==category.id
    assert eligibility(db,org.id,"opaque-synthetic-token",date(2026,12,1)) is None
    with pytest.raises(ReferenceConflict,match="overlapping"):
        enroll(db,actors[1],"opaque-synthetic-token",category.id,date(2026,6,1),date(2027,1,1))

def test_proposer_cannot_approve_own_contract(db):
    org,actors,auth=setup_actors(db)
    proposer,reviewer,precedence,activator=actors
    contract=create_draft(db,proposer,"HOSP-C",date(2027,1,1),date(2028,1,1))
    attach_authorization(db,reviewer,contract.id,auth.id)
    approve_precedence_policy(db,precedence,contract.id,"Independent written precedence decision for this contract")
    with pytest.raises(ReferenceConflict,match="proposal author"):
        approve_contract(db,contract.id,proposer,date(2026,10,10),precedence_approved=True)
    assert db.get(ContractVersion,contract.id).status=="draft"
