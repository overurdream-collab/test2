"""Actual PostgreSQL point guards; synthetic rows, no real health records."""
import os
from datetime import date, datetime, timezone
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from mcias.models import Organization, User
from mcias.models_reference_points import ReferencePoint


@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"), reason="isolated Postgres CI required")
def test_postgres_forbids_inserting_approved_and_mutating_or_deleting_points():
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(os.environ["MCIAS_TEST_DATABASE_URL"])
    with Session(engine, expire_on_commit=False) as db:
        org = Organization(name="SYN point-guard " + uuid4().hex[:8])
        db.add(org)
        db.flush()
        reviewer = User(organization_id=org.id, username="syn-point-guard-" + uuid4().hex,
                        password_hash="synthetic")
        db.add(reviewer)
        db.flush()
        point = ReferencePoint(organization_id=org.id, section="contracts",
            logical_key="term", version=1, title="Contract term",
            clause_text="Synthetic 12 months", rule_type="duration",
            effective_from=date(2026, 1, 1), effective_until=date(2027, 1, 1),
            status="draft", created_by=reviewer.id)
        db.add(point)
        db.commit()
        point_id, org_id, user_id = point.id, org.id, reviewer.id
    # Test owner-role raw SQL too; ORM immutability is not sufficient.
    with engine.begin() as conn:
        with pytest.raises(DBAPIError):
            with conn.begin_nested():
                conn.execute(text("""
                    INSERT INTO reference_points
                    (id, organization_id, section, logical_key, version, title,
                     clause_text, rule_type, effective_from, effective_until,
                     status, created_by, approved_by, approved_at, created_at)
                    VALUES (:id,:org,'contracts','forged',1,'forged',
                            'forged direct insert','duration','2026-01-01','2027-01-01',
                            'approved',:actor,:actor,now(),now())
                """), {"id":str(uuid4()),"org":org_id,"actor":user_id})
        # Savepoint rollback restores a usable transaction.
        with pytest.raises(DBAPIError):
            with conn.begin_nested():
                conn.execute(text("UPDATE reference_points SET title='HACK' WHERE id=:id"), {"id":point_id})
        with pytest.raises(DBAPIError):
            with conn.begin_nested():
                conn.execute(text("DELETE FROM reference_points WHERE id=:id"), {"id":point_id})
    with Session(engine, expire_on_commit=False) as db:
        point = db.get(ReferencePoint, point_id)
        assert point is not None and point.title == "Contract term" and point.status == "draft"
        point.status = "approved"
        point.approved_by = user_id
        point.approved_at = datetime.now(timezone.utc)
        db.commit()
    with engine.begin() as conn:
        with pytest.raises(DBAPIError):
            with conn.begin_nested():
                conn.execute(text("UPDATE reference_points SET clause_text='HACK' WHERE id=:id"), {"id":point_id})
        with pytest.raises(DBAPIError):
            with conn.begin_nested():
                conn.execute(text("DELETE FROM reference_points WHERE id=:id"), {"id":point_id})
    engine.dispose()
