"""G7 PostgreSQL migrations and append-only physical database guards."""
import os
import pytest
from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config

@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"),reason="PostgreSQL CI required")
def test_g7_schema_and_immutable_trigger():
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(os.environ["MCIAS_TEST_DATABASE_URL"])
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0019_reference_points"
        assert conn.execute(text("""SELECT count(*) FROM pg_trigger
             WHERE tgname='trg_g7_report_guard' AND NOT tgisinternal""")).scalar_one() == 1
        assert conn.execute(text("""SELECT count(*) FROM pg_constraint
             WHERE conname='uq_g7_report_batch_version'""")).scalar_one() == 1
    engine.dispose()
