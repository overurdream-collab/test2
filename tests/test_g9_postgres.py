"""G9 actual PostgreSQL least-privilege role test; no real institutional accounts."""
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from alembic import command
from alembic.config import Config

from mcias.preflight_g9 import check_postgres_role

@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"),
                    reason="dedicated PostgreSQL CI service required")
def test_g9_readonly_runtime_role_preflight_and_negative_mutation():
    command.upgrade(Config("alembic.ini"),"head")
    parsed=make_url(os.environ["MCIAS_TEST_DATABASE_URL"])
    synthetic_role="mcias_g9_runtime_"+uuid4().hex[:10]
    synthetic_password="CI_only_synthetic_role_password"
    admin=create_engine(parsed.render_as_string(hide_password=False),
                        isolation_level="AUTOCOMMIT")
    role_url=parsed.set(username=synthetic_role,password=synthetic_password)
    runtime=None
    try:
        with admin.connect() as connection:
            connection.execute(text(
                f'CREATE ROLE "{synthetic_role}" LOGIN PASSWORD \'{synthetic_password}\''
            ))
            connection.execute(text(
                f'GRANT USAGE ON SCHEMA public TO "{synthetic_role}"'))
            connection.execute(text(
                f'GRANT SELECT ON TABLE public.alembic_version TO "{synthetic_role}"'))
        runtime=create_engine(role_url.render_as_string(hide_password=False))
        checks=check_postgres_role(role_url.render_as_string(hide_password=False))
        states={item["control"]:item["status"] for item in checks}
        assert states=={
            "database.role_flags":"PASS",
            "database.schema_create":"PASS",
            "database.table_ownership":"PASS",
            "database.audit_mutation":"PASS",
            "database.migration_head":"PASS",
        }
        with pytest.raises(DBAPIError):
            with runtime.begin() as connection:
                connection.execute(text("UPDATE public.audit_log SET action='forbidden'"))
        with pytest.raises(DBAPIError):
            with runtime.begin() as connection:
                connection.execute(text("CREATE TABLE public.forbidden_runtime_ddl (x integer)"))
        with admin.connect() as connection:
            connection.execute(text(
                f'GRANT UPDATE ON public.audit_log TO "{synthetic_role}"'))
        states={item["control"]:item["status"] for item in check_postgres_role(
            role_url.render_as_string(hide_password=False))}
        assert states["database.audit_mutation"]=="BLOCKED"
    finally:
        if runtime is not None:
            runtime.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP OWNED BY "{synthetic_role}"'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{synthetic_role}"'))
        admin.dispose()
