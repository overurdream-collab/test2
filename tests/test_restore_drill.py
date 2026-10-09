"""G1 T17: PostgreSQL dump -> encrypted archive -> restored independent database."""
import os
import subprocess
import uuid
import pytest
from sqlalchemy import create_engine, text
from mcias.backup import encrypt_bundle, decrypt_bundle

def run(*args, env=None, input=None):
    return subprocess.run(args, input=input, env=env, capture_output=True, check=True).stdout

@pytest.mark.skipif(not os.environ.get("MCIAS_TEST_DATABASE_URL"), reason="requires isolated PostgreSQL CI")
def test_t17_postgres_restore_and_encrypted_bundle():
    url = os.environ["MCIAS_TEST_DATABASE_URL"]
    from sqlalchemy.engine import make_url
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql"
    password = parsed.password or ""
    pg_env = dict(os.environ, PGPASSWORD=password)
    base = ["-h", parsed.host or "localhost", "-p", str(parsed.port or 5432), "-U", parsed.username]
    source_db = parsed.database
    restore_db = "mcias_restore_" + uuid.uuid4().hex[:12]
    key = os.urandom(32)
    admin = create_engine(parsed.set(database="postgres").render_as_string(hide_password=False), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text('CREATE DATABASE "' + restore_db + '"'))
        try:
            with create_engine(url).begin() as conn:
                conn.execute(text("CREATE TABLE IF NOT EXISTS restore_probe (id integer primary key, payload text not null)"))
                conn.execute(text("INSERT INTO restore_probe VALUES (1701, 'synthetic restore proof') ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload"))
            dump = run("pg_dump", *base, "-Fc", "-d", source_db, env=pg_env)
            encrypted = encrypt_bundle({"database.dump": dump, "evidence.txt": b"synthetic"}, key)
            assert b"synthetic restore proof" not in encrypted
            recovered = decrypt_bundle(encrypted, key)
            assert recovered["database.dump"] == dump
            run("pg_restore", *base, "-d", restore_db, "--no-owner", "--no-privileges", env=pg_env, input=recovered["database.dump"])
            restored_url = parsed.set(database=restore_db).render_as_string(hide_password=False)
            restored_engine = create_engine(restored_url)
            try:
                with restored_engine.connect() as conn:
                    assert conn.execute(text("SELECT payload FROM restore_probe WHERE id=1701")).scalar_one() == "synthetic restore proof"
                    assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0003_mfa"
            finally:
                restored_engine.dispose()
        finally:
            with admin.connect() as conn:
                conn.execute(text('DROP DATABASE IF EXISTS "' + restore_db + '" WITH (FORCE)'))
    finally:
        admin.dispose()
