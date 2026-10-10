"""Reset means dropping a whole dedicated test DB, never disabling audit triggers."""
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

def reset(config, confirmation):
    config.validate()
    url = make_url(config.database_url)
    if confirmation != url.database:
        raise ValueError("confirmation must exactly match the dedicated database name")
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            quoted = connection.dialect.identifier_preparer.quote_identifier(url.database)
            # No FORCE or session termination; active connections make reset fail safely.
            connection.exec_driver_sql("DROP DATABASE " + quoted)
            connection.exec_driver_sql("CREATE DATABASE " + quoted)
    finally:
        admin.dispose()
