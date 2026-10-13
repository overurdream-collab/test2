"""G9 negative security tests: fail-closed release, TLS, bootstrap and backups."""
import io
import json
import os
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from mcias.backup import (encrypt_bundle, decrypt_bundle, MAGIC,
                          MAX_ENTRIES, MAX_BUNDLE_BYTES)
from mcias.preflight_g9 import check_runtime_env, check_certificate, check_postgres_role, report, safe_file
from mcias.release_g9 import (ReleaseBlocked, create_manifest, verify_manifest,
                              encode_receipt)

COMMIT = "b" * 40

def test_g9_manifest_pins_exact_artifact_hash_and_blocks_tampering(tmp_path):
    wheel=tmp_path/"mcias-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"synthetic wheel bytes; never a real medical file")
    manifest=create_manifest({"wheels/mcias-0.1.0-py3-none-any.whl":wheel},COMMIT)
    assert manifest["migration_head"] == "0022_rbac_authority"
    bundle=tmp_path/"bundle"
    (bundle/"wheels").mkdir(parents=True)
    copied=bundle/"wheels"/wheel.name
    copied.write_bytes(wheel.read_bytes())
    assert verify_manifest(manifest,bundle)
    copied.write_bytes(b"tampered")
    with pytest.raises(ReleaseBlocked,match="checksum"):
        verify_manifest(manifest,bundle)


@pytest.mark.skipif(not os.getenv("MCIAS_TEST_DATABASE_URL"),
                    reason="isolated PostgreSQL migration checks required")
@pytest.mark.parametrize("revision,expected", [
    ("0018_claim_query_indexes", "BLOCKED"),
    ("0019_rbac", "BLOCKED"),
    ("0021_organization_features", "BLOCKED"),
    ("0022_rbac_authority", "PASS"),
])
def test_g9_runtime_rejects_old_schema_and_accepts_rbac_schema(monkeypatch, revision, expected):
    """Check real migrated databases, without changing the shared suite's revision."""
    parsed = make_url(os.environ["MCIAS_TEST_DATABASE_URL"])
    marker = uuid4().hex[:12]
    database_name = "mcias_g9_revision_" + marker
    role_name = "mcias_g9_revision_role_" + marker
    password = "synthetic_revision_probe_only"
    admin = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    probe_url = parsed.set(database=database_name)
    probe_admin = None
    database_created = role_created = False
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{database_name}"'))
            database_created = True
        with monkeypatch.context() as context:
            context.setenv("MCIAS_TEST_DATABASE_URL", probe_url.render_as_string(hide_password=False))
            command.upgrade(Config("alembic.ini"), revision)
        probe_admin = create_engine(probe_url, isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            conn.execute(text(
                f'CREATE ROLE "{role_name}" LOGIN PASSWORD \'{password}\' '
                'NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'
            ))
            role_created = True
        with probe_admin.connect() as conn:
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == revision
            conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role_name}"'))
            conn.execute(text(f'GRANT SELECT ON TABLE public.alembic_version TO "{role_name}"'))
        runtime_url = probe_url.set(username=role_name, password=password)
        states = {item["control"]: item["status"] for item in check_postgres_role(
            runtime_url.render_as_string(hide_password=False)
        )}
        assert states == {
            "database.role_flags": "PASS",
            "database.schema_create": "PASS",
            "database.table_ownership": "PASS",
            "database.audit_mutation": "PASS",
            "database.migration_head": expected,
        }
    finally:
        if probe_admin is not None:
            probe_admin.dispose()
        try:
            with admin.connect() as conn:
                if database_created:
                    conn.execute(text(f'DROP DATABASE "{database_name}" WITH (FORCE)'))
                if role_created:
                    conn.execute(text(f'DROP ROLE "{role_name}"'))
        finally:
            admin.dispose()


def test_g9_manifest_rejects_traversal_symlink_and_forged_approval(tmp_path):
    wheel=tmp_path/"mcias.whl"
    wheel.write_bytes(b"safe")
    for name in ("../secrets.txt","/etc/password.txt","..\\secrets.txt",
                 "wheels/../../bad.whl","patient_data.csv","manifest.json"):
        with pytest.raises(ReleaseBlocked):
            create_manifest({name:wheel},COMMIT)
    with pytest.raises(ReleaseBlocked):
        create_manifest({"wheels/ok.whl":wheel},"main")
    receipt=create_manifest({"wheel.whl":wheel},COMMIT)
    receipt["acceptance"]="ACCEPTED"
    with pytest.raises(ReleaseBlocked,match="integrity"):
        verify_manifest(receipt,tmp_path)
    receipt=create_manifest({"wheel.whl":wheel},COMMIT)
    directory=tmp_path/"distribution"
    directory.mkdir()
    (directory/"wheel.whl").symlink_to(wheel)
    with pytest.raises(ReleaseBlocked):
        verify_manifest(receipt,directory)

def test_g9_preflight_never_claims_production_accepted_and_never_leaks_secrets():
    secret="1"*64
    raw={
        "MCIAS_ENVIRONMENT":"development",
        "MCIAS_BOOTSTRAP_TOKEN":"private-development-bootstrap-secret",
        "MCIAS_MFA_ENCRYPTION_KEY":secret,
        "MCIAS_DATABASE_URL":"postgresql+psycopg://user:very_private_password@localhost/test",
        "MCIAS_RELEASE_COMMIT":COMMIT,
    }
    outcome=report(raw)
    assert outcome["status"]=="BLOCKED"
    assert outcome["production_accepted"] is False
    dump=json.dumps(outcome)
    assert "very_private_password" not in dump
    assert secret not in dump
    assert "private-development-bootstrap-secret" not in dump
    status={row["control"]:row["status"] for row in outcome["controls"]}
    assert status["runtime.environment"]=="BLOCKED"
    assert status["bootstrap.disabled"]=="BLOCKED"
    assert status["database.runtime_probe"]=="BLOCKED"

def test_g9_preflight_disables_bootstrap_and_rejects_placeholder_keys(tmp_path):
    secure=tmp_path/"registry.json"
    secure.write_text('{"approvals":{},"trusted_heads":{}}')
    secure.chmod(0o600)
    raw={
        "MCIAS_ENVIRONMENT":"production",
        "MCIAS_DATABASE_URL":"postgresql+psycopg://runtime:secret@db/mcias",
        "MCIAS_BOOTSTRAP_TOKEN":"",
        "MCIAS_MFA_ENCRYPTION_KEY":"0"*64,
        "MCIAS_AUTHORIZATION_REGISTRY":str(secure),
        "MCIAS_RELEASE_COMMIT":COMMIT,
    }
    info={item["control"]:item["status"] for item in check_runtime_env(raw)}
    assert info["bootstrap.disabled"]=="PASS"
    assert info["database.postgresql"]=="PASS"
    assert info["keys.mfa_present"]=="BLOCKED"
    assert info["authorization.registry_permissions"]=="PASS"
    secure.chmod(0o666)
    assert not safe_file(str(secure))
    assert {item["control"]:item["status"] for item in check_runtime_env(raw)}[
        "authorization.registry_permissions"]=="BLOCKED"
    raw["MCIAS_DATABASE_URL"]="sqlite:////tmp/insurance.sqlite"
    assert {item["control"]:item["status"] for item in check_runtime_env(raw)}[
        "database.postgresql"]=="BLOCKED"

def generate_cert(hostname,days=45):
    private=Ed25519PrivateKey.generate()
    now=datetime.now(timezone.utc)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,hostname)])
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(private.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(days=1))
        .not_valid_after(now+timedelta(days=days))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(hostname)]),critical=False)
        .sign(private,algorithm=None))
    return cert.public_bytes(__import__("cryptography").hazmat.primitives.serialization.Encoding.PEM)

def test_g9_local_tls_cert_checks_exact_hostname_and_expiration(tmp_path):
    cert=tmp_path/"tls.crt"
    cert.write_bytes(generate_cert("mcias.intranet",45))
    cert.chmod(0o600)
    assert check_certificate(str(cert),"mcias.intranet")["status"]=="PASS"
    assert check_certificate(str(cert),"wrong.intranet")["status"]=="BLOCKED"
    cert.write_bytes(generate_cert("mcias.intranet",5))
    assert check_certificate(str(cert),"mcias.intranet")["status"]=="BLOCKED"
    cert.write_text("not a certificate")
    assert check_certificate(str(cert),"mcias.intranet")["status"]=="BLOCKED"

def synthetic_tar(items):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode="w") as tar:
        for name,data in items:
            info=tarfile.TarInfo(name)
            info.size=len(data)
            tar.addfile(info,io.BytesIO(data))
    return buffer.getvalue()

def authenticated(payload,key):
    nonce=os.urandom(12)
    return MAGIC+nonce+AESGCM(key).encrypt(nonce,payload,MAGIC)

def test_g9_bundle_refuses_special_tar_paths_and_manifest_spoofing():
    key=b"z"*32
    good=encrypt_bundle({"database.dump":b"synthetic_pg_dump",
                        "sources/012345":b"encrypted blob"},key)
    assert decrypt_bundle(good,key)=={
        "database.dump":b"synthetic_pg_dump","sources/012345":b"encrypted blob"}
    with pytest.raises(ValueError):
        encrypt_bundle({"../exfiltrate":b"oops"},key)
    with pytest.raises(ValueError):
        encrypt_bundle({"manifest.json":b"spoof"},key)
    with pytest.raises(ValueError):
        encrypt_bundle({"folder\\escape":b"oops"},key)
    unsafe=synthetic_tar([("../secret.txt",b"x"),("manifest.json",b"{}")])
    with pytest.raises(ValueError):
        decrypt_bundle(authenticated(unsafe,key),key)
    duplicate=synthetic_tar([("database.dump",b"x"),("database.dump",b"y"),
        ("manifest.json",b'{"database.dump":"deadbeef"}')])
    with pytest.raises(ValueError):
        decrypt_bundle(authenticated(duplicate,key),key)
    with pytest.raises(ValueError):
        decrypt_bundle(b"wrong header"+good,key)

def test_g9_bundle_rejects_bounded_size_and_nonbinary_payload():
    key=b"z"*32
    with pytest.raises(ValueError):
        encrypt_bundle({"blob":b"x"*(MAX_BUNDLE_BYTES+1)},key)
    with pytest.raises(ValueError):
        encrypt_bundle({"blob":"not bytes"},key)
    with pytest.raises(ValueError):
        decrypt_bundle(b"x"*(MAX_BUNDLE_BYTES+1024*1024+99),key)

def test_g9_offline_ed25519_signed_receipt_requires_independently_trusted_key(tmp_path):
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
    from mcias.release_sign_g9 import sign_release, verify_release_signature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    artifact=tmp_path/"mcias.whl"
    artifact.write_bytes(b"synthetic receipt proof only")
    output=tmp_path/"release"
    output.mkdir()
    (output/"mcias.whl").write_bytes(artifact.read_bytes())
    receipt=create_manifest({"mcias.whl":artifact},COMMIT)
    key=Ed25519PrivateKey.generate()
    private_path=tmp_path/"operator-signing-seed"
    private_path.write_bytes(key.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption()))
    private_path.chmod(0o600)
    public=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    signed=sign_release(receipt,output,private_path)
    assert signed["acceptance"]=="NOT_A_HUMAN_SIGNOFF"
    assert verify_release_signature(receipt,output,signed,public)
    impostor=Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    with pytest.raises(ReleaseBlocked,match="independent trust"):
        verify_release_signature(receipt,output,signed,impostor)
    signed["signature_hex"]="0"*128
    with pytest.raises(ReleaseBlocked,match="signature invalid"):
        verify_release_signature(receipt,output,signed,public)
    private_path.chmod(0o644)
    with pytest.raises(ReleaseBlocked,match="permissions"):
        sign_release(receipt,output,private_path)
