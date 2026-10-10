import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from alembic.config import Config
from alembic import command
from mcias.models import SourceFile, Claim, AuditLog

@pytest.fixture(scope="module")
def engine():
    url = os.getenv("MCIAS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL integration database not configured")
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    yield engine
    engine.dispose()

def test_migrations_reach_mfa_revision(engine):
    with engine.connect() as conn:
        assert conn.execute(text("select version_num from alembic_version")).scalar_one() == "0008_g3_guards"
        assert conn.execute(text("select to_regclass('public.mfa_factors')")).scalar_one() is not None

def test_claim_originals_protected_by_database(engine):
    with Session(engine) as db:
        source = SourceFile(sha256="a"*64, original_filename="synthetic.csv", storage_key="integration-test-source")
        db.add(source)
        db.flush()
        claim = Claim(source_id=source.id, original_payload={"synthetic": True}, original_claimed_amount=10, currency="YER")
        db.add(claim)
        db.commit()
        claim_id = claim.id
    with engine.begin() as conn:
        with pytest.raises(Exception):
            conn.execute(text("update claims set original_claimed_amount = 999 where id = :id"), {"id": claim_id})
    with engine.connect() as conn:
        assert str(conn.execute(text("select original_claimed_amount from claims where id=:id"), {"id": claim_id}).scalar_one()) == "10.00"

def test_audit_log_append_only_at_database(engine):
    with Session(engine) as db:
        event = AuditLog(action="integration_check", resource_type="synthetic")
        db.add(event)
        db.commit()
        event_id = event.id
    with engine.begin() as conn:
        with pytest.raises(Exception):
            conn.execute(text("delete from audit_log where id=:id"), {"id": event_id})
    with engine.connect() as conn:
        assert conn.execute(text("select count(*) from audit_log where id=:id"), {"id": event_id}).scalar_one() == 1


def test_runtime_database_role_cannot_delete_audit_or_disable_triggers(engine):
    with engine.begin() as conn:
        conn.execute(text("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mcias_runtime_probe') THEN CREATE ROLE mcias_runtime_probe NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; END IF; END $$"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO mcias_runtime_probe"))
        conn.execute(text("GRANT SELECT, INSERT ON audit_log TO mcias_runtime_probe"))
    with engine.connect() as conn:
        conn.execute(text("SET ROLE mcias_runtime_probe"))
        try:
            with pytest.raises(Exception):
                with conn.begin_nested():
                    conn.execute(text("DELETE FROM audit_log"))
        finally:
            conn.rollback()
    with engine.connect() as conn:
        conn.execute(text("SET ROLE mcias_runtime_probe"))
        try:
            with pytest.raises(Exception):
                with conn.begin_nested():
                    conn.execute(text("ALTER TABLE claims DISABLE TRIGGER trg_mcias_claim_guard"))
        finally:
            conn.rollback()
