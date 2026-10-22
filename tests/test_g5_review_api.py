"""Real HTTP authentication -> existing G5 review -> durable Shared Audit.

Uses native G2/G3/G4 helpers; no mocked audit, prebuilt snapshot or financial path.
SQLite provides local isolation; the coordinator also runs this suite on PG16.
"""
import json
import os
import time
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from mcias.app import app, get_db, get_rate_limit_db
from mcias.mfa import generate_totp
from mcias.models import (Base, AuditLog, MFAFactor, Organization, Permission,
    Role, RolePermission, User, UserRole)
from mcias.models_audit import AuditSnapshot
from mcias.security import hash_password
from mcias.storage import EncryptedStore
from test_g5_inputs_first_review import _claim, _execution, _references


@pytest.fixture
def review_http(tmp_path, monkeypatch):
    url = os.getenv("MCIAS_TEST_DATABASE_URL")
    schema = None
    if url:
        engine = create_engine(url)
        assert engine.dialect.name == "postgresql"
        schema = "g5_http_" + uuid4().hex
        with engine.begin() as connection:
            assert 160000 <= int(connection.scalar(text("SHOW server_version_num"))) < 170000
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        isolated = engine.execution_options(schema_translate_map={None: schema})
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        isolated = engine
    Base.metadata.create_all(isolated)
    key, secret = b"s" * 32, b"synthetic-totp-secret"
    monkeypatch.setenv("MCIAS_MFA_ENCRYPTION_KEY", key.hex())
    store = EncryptedStore(str(tmp_path / "encrypted"), b"e" * 32)
    with Session(isolated, expire_on_commit=False) as db:
        org = Organization(name="SYN-G5-HTTP")
        db.add(org); db.flush()
        actor = User(organization_id=org.id, username="SYN-HTTP-" + uuid4().hex,
            password_hash=hash_password("synthetic-http-password"))
        role = Role(code="super_admin")
        db.add_all([actor, role]); db.flush()
        db.add(UserRole(user_id=actor.id, role_id=role.id))
        for code in ("claims.read", "claims.import", "workspace.super_admin"):
            permission = Permission(code=code)
            db.add(permission); db.flush()
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        nonce = os.urandom(12)
        db.add(MFAFactor(user_id=actor.id, encrypted_secret=nonce + AESGCM(key).encrypt(
            nonce, secret, actor.id.encode()), enabled=True, last_accepted_counter=-1))
        db.commit()

        def dependency():
            with Session(isolated) as request_db:
                yield request_db

        previous = {dependency_key: app.dependency_overrides.get(dependency_key)
            for dependency_key in (get_db, get_rate_limit_db)}
        app.dependency_overrides[get_db] = dependency
        app.dependency_overrides[get_rate_limit_db] = dependency
        try:
            with TestClient(app) as client:
                login = client.post("/api/v1/auth/login", json={"username": actor.username,
                    "password": "synthetic-http-password", "totp_code": generate_totp(secret, int(time.time()) // 30)})
                assert login.status_code == 200, login.text
                token = login.json()["access_token"]
                yield db, actor, role, store, isolated, client, {"Authorization": "Bearer " + token}
        finally:
            for dependency_key, provider in previous.items():
                if provider is None:
                    app.dependency_overrides.pop(dependency_key, None)
                else:
                    app.dependency_overrides[dependency_key] = provider
    if schema:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


def _url(claim_id):
    return f"/api/v1/audits/claims/{claim_id}/review"


def _none_created(db):
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(AuditSnapshot)) == 0
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "claim_inputs_audited")) == 0


@pytest.mark.parametrize("authorization", [None, "Bearer SYN-invalid"])
def test_review_http_requires_valid_session(review_http, authorization):
    db, actor, role, store, engine, client, headers = review_http
    response = client.post(_url(uuid4()), headers={} if authorization is None else {"Authorization": authorization})
    assert response.status_code == 401
    _none_created(db)


@pytest.mark.parametrize("revoke", ["role", "permission", "mfa", "mfa_counter", "active"])
def test_review_http_rechecks_current_privilege_and_mfa(review_http, revoke):
    db, actor, role, store, engine, client, headers = review_http
    if revoke == "role":
        reader = Role(code="SYN-reader")
        db.add(reader); db.flush()
        permission = db.scalar(select(Permission).where(Permission.code == "claims.read"))
        db.add_all([RolePermission(role_id=reader.id, permission_id=permission.id),
            UserRole(user_id=actor.id, role_id=reader.id)])
        db.query(UserRole).filter_by(user_id=actor.id, role_id=role.id).delete()
    elif revoke == "permission":
        permission = db.scalar(select(Permission).where(Permission.code == "claims.read"))
        db.query(RolePermission).filter_by(role_id=role.id, permission_id=permission.id).delete()
    elif revoke == "mfa":
        db.get(MFAFactor, actor.id).enabled = False
    elif revoke == "mfa_counter":
        db.get(MFAFactor, actor.id).last_accepted_counter = -1
    else:
        actor.active = False
    db.commit()
    response = client.post(_url(uuid4()), headers=headers)
    assert response.status_code == (401 if revoke == "active" else 403)
    _none_created(db)


@pytest.mark.parametrize("payload", [
    {"review_only": False}, {"policy": {"approved": True}},
    {"a1_review_packet": {}}, {"financial_decision": "approve"}, {"evidence_store": "client-path"},
])
def test_review_http_accepts_no_execution_controls_from_client(review_http, payload):
    db, actor, role, store, engine, client, headers = review_http
    response = client.post(_url(uuid4()), headers=headers, json=payload)
    assert response.status_code == 422
    _none_created(db)


def test_review_http_hides_other_tenant_claim(review_http):
    db, actor, role, store, engine, client, headers = review_http
    claim, *_ = _claim(db, actor, store)
    foreign_org = Organization(name="SYN-FOREIGN")
    db.add(foreign_org); db.flush()
    outsider = User(organization_id=foreign_org.id, username="SYN-FOREIGN-" + uuid4().hex,
        password_hash=hash_password("synthetic-foreign-password"))
    db.add(outsider); db.flush()
    db.add(UserRole(user_id=outsider.id, role_id=role.id))
    foreign_secret, nonce = b"synthetic-foreign-totp", os.urandom(12)
    db.add(MFAFactor(user_id=outsider.id, encrypted_secret=nonce + AESGCM(
        bytes.fromhex(os.environ["MCIAS_MFA_ENCRYPTION_KEY"])).encrypt(nonce, foreign_secret, outsider.id.encode()),
        enabled=True, last_accepted_counter=-1))
    db.commit()
    login = client.post("/api/v1/auth/login", json={"username": outsider.username,
        "password": "synthetic-foreign-password",
        "totp_code": generate_totp(foreign_secret, int(time.time()) // 30)})
    assert login.status_code == 200
    token = login.json()["access_token"]
    for claim_id in (claim.id, str(uuid4())):
        response = client.post(_url(claim_id), headers={"Authorization": "Bearer " + token})
        assert response.status_code == 404
        assert response.json() == {"detail": "claim not found"}
    _none_created(db)


@pytest.mark.parametrize("scenario, expected", [
    ("match", "MATCH_VERIFIED"), ("tariff", "VIOLATION_PROVEN"),
    ("absent_incomplete", "UNRESOLVED"), ("unreadable_source", "AUDIT_UNAVAILABLE"),
])
def test_review_http_runs_native_review_commits_and_retries_once(review_http, scenario, expected):
    db, actor, role, store, engine, client, headers = review_http
    claim, document, batch = _claim(db, actor, store,
        price="120" if scenario == "tariff" else "100", copay="24" if scenario == "tariff" else "20")
    _references(db, actor, store, scenario)
    _execution(db, actor, store, claim, scenario)
    if scenario == "unreadable_source":
        document.status = "failed"
        db.commit()
    response = client.post(_url(claim.id), headers=headers)
    assert response.status_code == 200, response.text
    snapshot = response.json()
    assert snapshot["claim_id"] == claim.id
    assert snapshot["findings"]["audit_state"] == expected
    assert snapshot["findings"]["audit_state_schema_version"] == 2
    assert snapshot["calculation"]["status"] == "held"
    assert snapshot["calculation"]["mode"] == "inputs_first_review"
    assert snapshot["calculation"]["payable"] is None and snapshot["calculation"]["deductions"] == []
    assert snapshot["findings"]["financial_decision"] == "not_authorized"
    assert snapshot["findings"]["human_review_required"] is True
    assert snapshot["verification"]["status"] == "held"
    assert response.headers["Cache-Control"] == "no-store"
    repeated = client.post(_url(claim.id), headers=headers, json={})
    assert repeated.status_code == 200 and repeated.json() == snapshot
    read = client.get(f'/api/v1/audits/{snapshot["id"]}', headers=headers)
    assert read.status_code == 200 and read.json() == snapshot
    with Session(engine) as independent:
        persisted = independent.get(AuditSnapshot, snapshot["id"])
        assert persisted.claim_id == claim.id and persisted.organization_id == actor.organization_id
        events = independent.scalars(select(AuditLog).where(AuditLog.action == "claim_inputs_audited")).all()
        assert len(events) == 1 and events[0].details["audit_snapshot_id"] == persisted.id
        assert events[0].details["audit_state"] == expected
        assert len(events[0].details["references"]) == 6
        details = json.dumps(events[0].details)
        assert all(value not in details for value in ("SYN-BEN", "SYN-PROVIDER", "SYN-CLAIM"))
        assert independent.scalar(select(func.count()).select_from(AuditSnapshot)) == 1
