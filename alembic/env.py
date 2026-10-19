"""Migration environment. Database URL is supplied from local MCIAS settings."""
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool
from mcias.config import Settings
import os

def migration_database_url():
    """Fail closed on ambiguous targets; never print connection strings.

    A test target is authorized only for an explicitly isolated local test
    execution. Server identity still requires an independent deployment-side
    attestation; URL validation is not a database-identity proof.
    """
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import ArgumentError

    target = os.environ.get("MCIAS_MIGRATION_TARGET", "").strip()
    environment = os.environ.get("MCIAS_ENVIRONMENT", "development").strip().lower()
    test_url = os.environ.get("MCIAS_TEST_DATABASE_URL")
    runtime_url = os.environ.get("MCIAS_DATABASE_URL")

    def reject(code):
        raise ValueError(code)

    if target not in {"test", "runtime"}:
        reject("ALEMBIC_TARGET_AMBIGUOUS")
    if target == "test":
        if environment == "production":
            reject("ALEMBIC_TARGET_FORBIDDEN")
        if environment != "test" or not test_url or (runtime_url and runtime_url != test_url):
            reject("ALEMBIC_TARGET_AMBIGUOUS")
        selected = test_url
    else:
        if test_url is not None or not runtime_url or environment == "test":
            reject("ALEMBIC_TARGET_AMBIGUOUS")
        selected = runtime_url

    try:
        parsed = make_url(selected)
        if (parsed.drivername != "postgresql+psycopg" or not parsed.database
                or not parsed.username or not parsed.host or not parsed.password):
            reject("ALEMBIC_TARGET_INVALID")
        if target == "test":
            import ipaddress
            # Private-network alone is not sufficient: tests must use loopback.
            if parsed.host != "localhost":
                if not ipaddress.ip_address(parsed.host).is_loopback:
                    reject("ALEMBIC_TARGET_FORBIDDEN")
            if parsed.database != "mcias_ci" and not parsed.database.endswith("_e2e"):
                reject("ALEMBIC_TARGET_FORBIDDEN")
    except (ValueError, TypeError, AttributeError, ArgumentError) as exc:
        if str(exc).startswith("ALEMBIC_TARGET_"):
            raise
        reject("ALEMBIC_TARGET_INVALID")
    return selected
from mcias.models import Base
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=migration_database_url(), target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    engine = create_engine(migration_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
