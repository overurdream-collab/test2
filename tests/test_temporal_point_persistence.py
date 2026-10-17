"""Synthetic persistence tests for immutable temporal reference clauses."""
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, SourceFile, WrittenAuthorization
from mcias.models_reference_points import ReferencePoint, ReferencePointClosure
from mcias.reference_points import create_draft, approve, as_dict, list_points, PointConflict, MAX_DATE


@pytest.fixture
def state():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        org = Organization(name="SYN temporal audit")
        db.add(org)
        db.flush()
        actors = [User(organization_id=org.id, username="syn-point-" + str(i),
                       password_hash="synthetic") for i in range(3)]
        db.add_all(actors)
        db.flush()
        source = SourceFile(sha256="b" * 64, original_filename="synthetic-auth.pdf",
                            storage_key="synthetic-point-authorization")
        db.add(source)
        db.flush()
        auth = WrittenAuthorization(organization_id=org.id, source_id=source.id,
                                    approved_by=actors[1].id, approved_at=datetime.now(timezone.utc))
        db.add(auth)
        db.commit()
        yield db, org, actors, auth
    engine.dispose()


def clause(start, *, end=MAX_DATE, supersedes=None, price="5000"):
    return dict(section="tariffs", logical_key="HOSP-A:CONSULT",
        title="Consultation", clause_text="Synthetic approved consultation amount",
        rule_type="amount", provider_code="HOSP-A", service_code="CONSULT",
        amount=Decimal(price), currency="YER",
        effective_from=start, effective_until=end, supersedes_id=supersedes,
        source_document_id=None, source_locator=None)


def test_replace_one_provider_price_preserves_historical_version(state):
    db, org, (writer, issuer, reviewer), auth = state
    earlier = date(2026, 1, 1)
    new_from = date.today() + timedelta(days=12)
    original = create_draft(db, writer, clause(earlier))
    approve(db, reviewer, original.id, auth.id, "Signed initial tariff synthetic test approval")
    successor = create_draft(db, writer, clause(new_from, supersedes=original.id, price="5500"))
    assert successor.status == "draft"
    assert db.get(ReferencePointClosure, original.id) is None
    approve(db, reviewer, successor.id, auth.id, "Signed tariff amendment synthetic test approval")
    closed = db.get(ReferencePointClosure, original.id)
    assert closed.effective_until == new_from
    assert closed.replaced_by_id == successor.id
    older = list_points(db, org.id, "tariffs", earlier)
    newer = list_points(db, org.id, "tariffs", new_from)
    assert len(older) == 1 and older[0]["amount"] == "5000.0000"
    assert len(newer) == 1 and newer[0]["amount"] == "5500.0000"
    assert len(list_points(db, org.id, "tariffs")) == 2


def test_never_delete_or_update_approved_point(state):
    db, org, (writer, issuer, reviewer), auth = state
    item = create_draft(db, writer, clause(date(2026, 1, 1)))
    approve(db, reviewer, item.id, auth.id, "Signed immutable clause synthetic approval")
    item.title = "MUTATED"
    with pytest.raises(ValueError, match="only transition"):
        db.flush()
    db.rollback()
    item = db.get(ReferencePoint, item.id)
    db.delete(item)
    with pytest.raises(ValueError, match="immutable"):
        db.flush()
    db.rollback()


def test_no_retroactive_amendment_without_independent_impact_workflow(state):
    db, org, (writer, issuer, reviewer), auth = state
    original = create_draft(db, writer, clause(date(2026, 1, 1)))
    approve(db, reviewer, original.id, auth.id, "Signed baseline synthetic approval rationale")
    with pytest.raises(PointConflict, match="retroactive"):
        create_draft(db, writer, clause(date(2026, 6, 1), supersedes=original.id))
    db.rollback()


def test_writer_cannot_approve_own_clause(state):
    db, org, (writer, issuer, reviewer), auth = state
    draft = create_draft(db, writer, clause(date(2026, 1, 1)))
    with pytest.raises(PointConflict, match="independent"):
        approve(db, writer, draft.id, auth.id, "Attempt to self-approve a clause")
    db.rollback()
    assert db.get(ReferencePoint, draft.id).status == "draft"
