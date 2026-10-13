"""Real 0021 schema and least-privilege feature lifecycle, not a DBA-only proof."""
import os
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import text, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from mcias.models_features import OrganizationFeature
from mcias.services import feature_service as f
from mcias.feature_runtime import setup

@pytest.mark.skipif(not os.getenv("MCIAS_RBAC_API_DATABASE_URL"), reason="isolated PostgreSQL RBAC database required")
def test_feature_runtime_grants_closure_triggers_and_transaction_rollback(api_factory):
    a = api_factory(url=os.environ["MCIAS_RBAC_API_DATABASE_URL"])
    role = "mcias_feature_probe_" + uuid4().hex[:10]
    with a.engine.begin() as conn:
        conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
        conn.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{role}"'))
        conn.execute(text(f'GRANT INSERT ON audit_log TO "{role}"'))
    setup(a.engine,role)
    setup(a.engine,role)  # repeat provisioning must preserve grants and records
    try:
        with a.engine.connect() as conn:
            conn.execute(text(f'SET ROLE "{role}"'))
            assert conn.scalar(text("SELECT has_column_privilege(current_user,'users','password_hash','UPDATE')")) is False
            assert conn.scalar(text("SELECT has_table_privilege(current_user,'organization_features','UPDATE')")) is False
            conn.commit()
            with Session(bind=conn) as db:
                assert len(f.list_features(db)) == 45
                row = f.grant_feature(db, a.organization_id, "inputs.contracts", a.ids["root"])
                db.commit()
                record_id = row.id
                f.revoke_feature(db, a.organization_id, row.feature_code, a.ids["root"], "Runtime closure")
                db.commit()
                assert f.grant_feature(db, a.organization_id, row.feature_code, a.ids["root"]).version == 2
                db.commit()
                with pytest.raises(DBAPIError):
                    with db.begin_nested(): db.execute(text("UPDATE organization_features SET version=50 WHERE id=:id"), {"id": record_id})
                with pytest.raises(DBAPIError):
                    with db.begin_nested(): db.execute(text("DELETE FROM organization_features WHERE id=:id"), {"id": record_id})
                with pytest.raises(DBAPIError):
                    with db.begin_nested(): db.execute(text("UPDATE organization_features SET close_reason='mutated' WHERE id=:id"), {"id": record_id})
                revision = f.grant_revision(db, a.organization_id)
                with pytest.raises(ValueError): f.replace_features(db, a.organization_id, [], a.ids["root"], "", revision)
                assert f.check_feature(db, a.organization_id, "inputs.contracts")
            conn.rollback()
            conn.execute(text("RESET ROLE")); conn.commit()
    finally:
        with a.engine.begin() as conn:
            conn.execute(text(f'DROP OWNED BY "{role}"'))
            conn.execute(text(f'DROP ROLE "{role}"'))
