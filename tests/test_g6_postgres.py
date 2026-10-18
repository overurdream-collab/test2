"""G6 PostgreSQL evidence integrity smoke tests."""
import os
import pytest
from sqlalchemy import create_engine,text
from alembic.config import Config
from alembic import command

@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"),reason="PostgreSQL required")
def test_g6_migration_and_immutable_trigger():
    command.upgrade(Config("alembic.ini"),"head")
    engine=create_engine(os.environ["MCIAS_TEST_DATABASE_URL"])
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()=="0020_manual_contract_metadata"
        assert conn.execute(text("SELECT count(*) FROM pg_trigger WHERE tgname='trg_g6_event_immutable' AND NOT tgisinternal")).scalar_one()==1
        assert conn.execute(text("SELECT count(*) FROM pg_constraint WHERE conname='uq_g6_case_version'")).scalar_one()==1
    engine.dispose()
