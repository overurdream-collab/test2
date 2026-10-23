"""G5 PostgreSQL migration and immutable evidence trigger verification."""
import os
import pytest
from sqlalchemy import create_engine,text
from alembic.config import Config
from alembic import command

@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"),reason="PostgreSQL CI required")
def test_g5_snapshot_trigger_and_migration():
    command.upgrade(Config("alembic.ini"),"head")
    engine=create_engine(os.environ["MCIAS_TEST_DATABASE_URL"])
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()=="0023_insurer_intake"
        assert conn.execute(text("""SELECT count(*) FROM pg_trigger
          WHERE tgname='trg_g5_audit_snapshot' AND NOT tgisinternal""")).scalar_one()==1
        assert conn.execute(text("SELECT count(*) FROM pg_trigger WHERE tgname='trg_g5_grant_guard' AND NOT tgisinternal")).scalar_one()==1
        assert conn.execute(text("SELECT count(*) FROM pg_trigger WHERE tgname='trg_g5_grant_guard' AND NOT tgisinternal")).scalar_one()==1
    engine.dispose()
