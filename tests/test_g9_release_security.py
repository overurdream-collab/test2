"""G9 negative security tests: fail-closed release, TLS, bootstrap and backups."""
import io
import json
import os
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from mcias.backup import (encrypt_bundle, decrypt_bundle, MAGIC,
                          MAX_ENTRIES, MAX_BUNDLE_BYTES)
from mcias.preflight_g9 import check_runtime_env, check_certificate, report, safe_file
from mcias.release_g9 import (ReleaseBlocked, create_manifest, verify_manifest,
                              encode_receipt)

COMMIT = "b" * 40

def test_g9_manifest_pins_exact_artifact_hash_and_blocks_tampering(tmp_path):
    wheel=tmp_path/"mcias-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"synthetic wheel bytes; never a real medical file")
    manifest=create_manifest({"wheels/mcias-0.1.0-py3-none-any.whl":wheel},COMMIT)
    bundle=tmp_path/"bundle"
    (bundle/"wheels").mkdir(parents=True)
    copied=bundle/"wheels"/wheel.name
    copied.write_bytes(wheel.read_bytes())
    assert verify_manifest(manifest,bundle)
    copied.write_bytes(b"tampered")
    with pytest.raises(ReleaseBlocked,match="checksum"):
        verify_manifest(manifest,bundle)

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
