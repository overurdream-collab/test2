"""Migration environment. Database URL is supplied from local MCIAS settings."""
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool
from mcias.config import Settings
import os

def migration_database_url():
    return os.environ.get('MCIAS_TEST_DATABASE_URL') or Settings().database_url
from mcias.models import Base
from mcias import models_reference_points  # noqa: F401 - migration metadata
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
