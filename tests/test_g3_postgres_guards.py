"""PostgreSQL G3 database-level acceptance: constraints resist raw SQL bypass."""
import os
import uuid
import pytest
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command

@pytest.fixture(scope="module")
def engine():
    url=os.getenv("MCIAS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("requires PostgreSQL CI")
    command.upgrade(Config("alembic.ini"), "head")
    engine=create_engine(url)
    yield engine
    engine.dispose()

def test_g3_postgres_constraints_and_guards(engine):
    org=str(uuid.uuid4())
    first=str(uuid.uuid4())
    second=str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (id,name,created_at) VALUES (:id,'g3 synthetic',now())"),{"id":org})
        conn.execute(text("""INSERT INTO contract_versions
            (id,organization_id,provider_code,version,effective_from,effective_until,status,precedence,created_at)
            VALUES (:id,:org,'H1',1,'2026-01-01','2026-06-01','approved',0,now())"""),{"id":first,"org":org})
    with engine.begin() as conn:
        with pytest.raises(Exception):
            with conn.begin_nested():
                conn.execute(text("""INSERT INTO contract_versions
                    (id,organization_id,provider_code,version,effective_from,effective_until,status,precedence,created_at)
                    VALUES (:id,:org,'H1',2,'2026-05-01','2026-12-01','approved',0,now())"""),
                    {"id":second,"org":org})
    with engine.begin() as conn:
        with pytest.raises(Exception):
            with conn.begin_nested():
                conn.execute(text("UPDATE contract_versions SET effective_until='2026-12-01' WHERE id=:id"),{"id":first})
    with engine.begin() as conn:
        with pytest.raises(Exception):
            with conn.begin_nested():
                conn.execute(text("DELETE FROM contract_versions WHERE id=:id"),{"id":first})
    with engine.connect() as conn:
        assert conn.execute(text("SELECT effective_until FROM contract_versions WHERE id=:id"),{"id":first}).scalar_one().isoformat()=="2026-06-01"

def test_g3_beneficiary_cross_tenant_guard(engine):
    org1,org2,category,enrollment=[str(uuid.uuid4()) for _ in range(4)]
    with engine.begin() as conn:
        for org in (org1,org2):
            conn.execute(text("INSERT INTO organizations (id,name,created_at) VALUES (:id,'g3 tenant',now())"),{"id":org})
        conn.execute(text("INSERT INTO beneficiary_categories (id,organization_id,code,description) VALUES (:id,:org,'A','synthetic')"),
                     {"id":category,"org":org1})
    with engine.begin() as conn:
        with pytest.raises(Exception):
            with conn.begin_nested():
                conn.execute(text("""INSERT INTO beneficiary_enrollments
                    (id,organization_id,beneficiary_token,category_id,effective_from,effective_until)
                    VALUES (:id,:org,'synthetic',:category,'2026-01-01','2027-01-01')"""),
                    {"id":enrollment,"org":org2,"category":category})
