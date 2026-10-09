import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from alembic.config import Config
from alembic import command
from mcias.models import Organization, RuleVersion

@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"), reason="requires PostgreSQL CI")
def test_activated_rule_is_immutable_in_database():
    url = os.environ["MCIAS_TEST_DATABASE_URL"]
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    try:
        with Session(engine) as db:
            org = Organization(name="synthetic-rule-guard")
            db.add(org)
            db.flush()
            rule = RuleVersion(organization_id=org.id, rule_type="synthetic", status="active")
            db.add(rule)
            db.commit()
            rule_id = rule.id
        with pytest.raises(Exception):
            with engine.begin() as conn:
                conn.execute(text("UPDATE rule_versions SET status='draft' WHERE id=:id"), {"id": rule_id})
        with pytest.raises(Exception):
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM rule_versions WHERE id=:id"), {"id": rule_id})
        with engine.connect() as conn:
            assert conn.execute(text("SELECT status FROM rule_versions WHERE id=:id"), {"id": rule_id}).scalar_one() == "active"
    finally:
        engine.dispose()
