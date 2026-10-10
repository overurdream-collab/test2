"""G3 PostgreSQL approved tariff immutability and temporal boundaries."""
import os
import uuid
import pytest
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command

@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"),reason="PostgreSQL CI required")
def test_g3_approved_tariff_cannot_change_via_raw_sql():
    url=os.environ["MCIAS_TEST_DATABASE_URL"]
    command.upgrade(Config("alembic.ini"),"head")
    engine=create_engine(url)
    org,contract,tariff=[str(uuid.uuid4()) for _ in range(3)]
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (id,name,created_at) VALUES (:id,'synthetic',now())"),{"id":org})
        conn.execute(text("""INSERT INTO contract_versions
          (id,organization_id,provider_code,version,effective_from,effective_until,status,precedence,created_at)
          VALUES (:id,:org,'P',1,'2027-01-01','2028-01-01','draft',0,now())"""),
          {"id":contract,"org":org})
        conn.execute(text("""INSERT INTO provider_tariffs (id,contract_id,service_code,amount,currency)
          VALUES (:id,:contract,'CONSULT',123.45,'YER')"""),{"id":tariff,"contract":contract})
        conn.execute(text("UPDATE contract_versions SET status='approved' WHERE id=:id"),{"id":contract})
    with engine.begin() as conn:
        with pytest.raises(Exception):
            with conn.begin_nested():
                conn.execute(text("UPDATE provider_tariffs SET amount=0 WHERE id=:id"),{"id":tariff})
        with pytest.raises(Exception):
            with conn.begin_nested():
                conn.execute(text("DELETE FROM provider_tariffs WHERE id=:id"),{"id":tariff})
    with engine.connect() as conn:
        assert str(conn.execute(text("SELECT amount FROM provider_tariffs WHERE id=:id"),{"id":tariff}).scalar_one())=="123.4500"
    engine.dispose()
