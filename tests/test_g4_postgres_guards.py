"""G4 database provenance enforcement smoke test against real PostgreSQL."""
import os
import pytest
from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config

@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"),reason="PostgreSQL required")
def test_g4_provenance_guards_installed():
    command.upgrade(Config("alembic.ini"),"head")
    engine=create_engine(os.environ["MCIAS_TEST_DATABASE_URL"])
    with engine.connect() as conn:
        rows=conn.execute(text("""
          SELECT tgname, tgrelid::regclass::text AS tablename
          FROM pg_trigger
          WHERE NOT tgisinternal AND tgname LIKE 'trg_g4_%'
        """)).all()
        names={(row[0],row[1]) for row in rows}
        assert ("trg_g4_claim_entries","claim_entries") in names
        assert ("trg_g4_claim_attachments","claim_attachments") in names
    engine.dispose()
