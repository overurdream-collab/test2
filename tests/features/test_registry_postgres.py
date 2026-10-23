import os
from uuid import uuid4
from datetime import date
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError
from mcias.models import User
from mcias.schemas.registry import RecordCreate
from mcias.services import feature_service as f, registry_service as r

@pytest.mark.skipif(not os.getenv('MCIAS_RBAC_API_DATABASE_URL'),reason='isolated PostgreSQL runtime database required')
def test_encrypted_intake_lifecycle_works_without_update_or_delete(api_factory,monkeypatch,tmp_path):
    a=api_factory(url=os.environ['MCIAS_RBAC_API_DATABASE_URL'])
    monkeypatch.setenv('MCIAS_STORAGE_DIR',str(tmp_path/'sources'));monkeypatch.setenv('MCIAS_STORAGE_KEY','22'*32)
    with Session(a.engine) as db:f.grant_feature(db,a.organization_id,'providers.labs',a.ids['root']);db.commit()
    role='mcias_intake_probe_'+uuid4().hex[:10]
    with a.engine.begin() as conn:
        conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
        conn.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{role}"'))
        conn.execute(text(f'GRANT INSERT ON source_files, audit_log TO "{role}"'))
    try:
        with a.engine.connect() as conn:
            conn.execute(text(f'SET ROLE "{role}"'));conn.commit()
            with Session(bind=conn) as db:
                actor=db.get(User,a.ids['admin'])
                row=r.create_record(db,actor,'providers.labs',RecordCreate(title='SYN-Lab',effective_from=date.today(),values={'record_code':'SYN-LAB','provider_code':'SYN-LAB'}));db.commit()
                closed=r.close_record(db,actor,'providers.labs',row['id'],1,'Runtime closure');db.commit()
                assert closed['status']=='closed'
                assert len(r.record_history(db,actor,'providers.labs',row['id']))==2
                with pytest.raises(DBAPIError):
                    with db.begin_nested():db.execute(text("DELETE FROM audit_log WHERE resource_id=:id"),{'id':row['id']})
                with pytest.raises(DBAPIError):
                    with db.begin_nested():db.execute(text("UPDATE source_files SET sha256='bad' WHERE id=:id"),{'id':row['source_id']})
            conn.rollback();conn.execute(text('RESET ROLE'));conn.commit()
    finally:
        with a.engine.begin() as conn:
            conn.execute(text(f'DROP OWNED BY "{role}"'));conn.execute(text(f'DROP ROLE "{role}"'))
