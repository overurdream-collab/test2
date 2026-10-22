"""G2 upload -> existing G3 dataset service over real authenticated HTTP."""
import base64
import csv
import hashlib
from io import StringIO
import json
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from mcias.app import app, get_db
from mcias.bootstrap_mfa import provision_privileged_factor
from mcias.mfa import generate_totp
from mcias.models import (Base, Organization, User, Role, UserRole, Permission,
    RolePermission, AuditLog)
from mcias.models_ingestion import ExtractedSourceRecord
from mcias.models_reference import ReferenceDatasetVersion
from mcias.security import hash_password

PASSWORD = "SYN-reference-http-password"
BASE = "/api/v1/reference/datasets"


def source_bytes():
    payload = dict(effective_from="2026-01-01", effective_until="2027-01-01",
        beneficiary_token="SYN-B1", employee_token="SYN-E1", relationship="child",
        category_code="SYN-C1", covered_services=["SYN-S1"], eligible=True)
    buffer = StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["record_key", "payload"])
    writer.writerow(["SYN-R1", json.dumps(payload)])
    return buffer.getvalue().encode()


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("MCIAS_ENVIRONMENT", "development")
    monkeypatch.setenv("MCIAS_MALWARE_SCAN", "disabled")
    monkeypatch.setenv("MCIAS_STORAGE_KEY", "64" * 32)
    monkeypatch.setenv("MCIAS_STORAGE_DIR", str(tmp_path / "sources"))
    monkeypatch.setenv("MCIAS_MFA_ENCRYPTION_KEY", "65" * 32)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, foreign_org = Organization(name="SYN-http-owner"), Organization(name="SYN-http-foreign")
        db.add_all([org, foreign_org]); db.flush()
        roles = {code: Role(code=code) for code in ("super_admin", "reference_writer", "reference_reader", "grant_only")}
        permissions = {code: Permission(code=code) for code in (
            "workspace.super_admin", "ingestion.upload", "reference.write", "reference.read", "reference.approve")}
        db.add_all([*roles.values(), *permissions.values()]); db.flush()
        for role, grants in (("super_admin", ("workspace.super_admin", "ingestion.upload")),
                ("reference_writer", ("reference.write", "ingestion.upload")),
                ("reference_reader", ("reference.read",)),
                ("grant_only", ("workspace.super_admin", "reference.approve"))):
            db.add_all([RolePermission(role_id=roles[role].id, permission_id=permissions[code].id) for code in grants])
        password_hash = hash_password(PASSWORD)
        users = {}
        for name, role in (("admin", "super_admin"), ("foreign", "super_admin"),
                           ("writer", "reference_writer"), ("reader", "reference_reader"), ("grant_only", "grant_only")):
            user = User(organization_id=foreign_org.id if name == "foreign" else org.id,
                username="SYN-" + name + "-" + uuid4().hex, password_hash=password_hash)
            db.add(user); db.flush()
            db.add(UserRole(user_id=user.id, role_id=roles[role].id))
            users[name] = {"id": user.id, "username": user.username}
        db.commit()
        secrets = {}
        for name in ("admin", "foreign"):
            encoded = provision_privileged_factor(db, users[name]["username"], bytes.fromhex("65" * 32))
            secrets[name] = base64.b32decode(encoded + "=" * (-len(encoded) % 8))
        super_permission_id = permissions["workspace.super_admin"].id
        super_role_id = roles["super_admin"].id

    def dependency():
        with Session(engine) as db:
            yield db
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = dependency
    try:
        with TestClient(app) as client:
            headers = {}
            for name, user in users.items():
                body = {"username": user["username"], "password": PASSWORD}
                if name in secrets:
                    body["totp_code"] = generate_totp(secrets[name], int(time.time()) // 30)
                response = client.post("/api/v1/auth/login", json=body)
                assert response.status_code == 200, response.text
                headers[name] = {"Authorization": "Bearer " + response.json()["access_token"]}
            yield SimpleNamespace(client=client, engine=engine, headers=headers, users=users,
                super_permission_id=super_permission_id, super_role_id=super_role_id)
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
        engine.dispose()


def uploaded(world):
    raw = source_bytes()
    response = world.client.post("/api/v1/ingestion/uploads", params={"filename": "SYN-reference.csv"},
        content=raw, headers=world.headers["admin"])
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "extracted"
    return response.json()["document_id"], hashlib.sha256(raw).hexdigest()


def definition(document_id, **changes):
    body = dict(document_id=document_id, family="beneficiary", dataset_key="SYN-beneficiary",
        version=1, effective_from="2026-01-01", effective_until="2027-01-01",
        coverage_from="2026-01-01", coverage_until="2027-01-01",
        scope={"all_providers": True, "all_services": True, "all_beneficiaries": True}, expected_record_count=1)
    return {**body, **changes}


def registered(world):
    document_id, sha256 = uploaded(world)
    response = world.client.post(BASE, json=definition(document_id), headers=world.headers["admin"])
    assert response.status_code == 201, response.text
    return response.json(), sha256


def test_http_real_source_approval_metadata_and_retry_after_commit(world):
    draft, sha256 = registered(world)
    assert draft["status"] == "draft" and draft["source_sha256"] == sha256
    assert draft["approved_by"] is None and draft["approval_event_id"] is None
    with Session(world.engine) as independent:
        assert independent.get(ReferenceDatasetVersion, draft["id"]).source_sha256 == sha256
    body = {"reason_code": "source_scope_complete"}
    approved = world.client.post(BASE + "/" + draft["id"] + "/approve", json=body, headers=world.headers["admin"])
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_by"] == world.users["admin"]["id"]
    retry = world.client.post(BASE + "/" + draft["id"] + "/approve", json=body, headers=world.headers["admin"])
    assert retry.status_code == 200
    assert retry.json()["approval_event_id"] == approved.json()["approval_event_id"]
    metadata = world.client.get(BASE + "/" + draft["id"], headers=world.headers["admin"])
    assert metadata.status_code == 200
    assert metadata.json()["approval_event_id"] == approved.json()["approval_event_id"]
    assert not set(metadata.json()).intersection({"records", "payload", "scope", "filename", "values"})
    assert "SYN-B1" not in metadata.text
    with Session(world.engine) as independent:
        persisted = independent.get(ReferenceDatasetVersion, draft["id"])
        assert persisted.status == "approved"
        events = independent.scalars(select(AuditLog).where(AuditLog.action == "reference_dataset_approved")).all()
        assert len(events) == 1 and events[0].id == persisted.approval_event_id


def test_http_authentication_role_permission_and_mfa_are_real(world):
    draft, _ = registered(world)
    assert world.client.get(BASE + "/" + draft["id"]).status_code == 401
    for name in ("writer", "reader", "grant_only"):
        response = world.client.post(BASE + "/" + draft["id"] + "/approve",
            json={"reason_code": "source_scope_complete"}, headers=world.headers[name])
        assert response.status_code == 403
        assert world.client.get(BASE + "/" + draft["id"], headers=world.headers[name]).status_code == 403
    # Role alone does not preserve access when the durable permission is revoked.
    with Session(world.engine) as db:
        grant = db.get(RolePermission, (world.super_role_id, world.super_permission_id))
        db.delete(grant); db.commit()
    assert world.client.post(BASE + "/" + draft["id"] + "/approve",
        json={"reason_code": "source_scope_complete"}, headers=world.headers["admin"]).status_code == 403
    missing_mfa = world.client.post("/api/v1/auth/login", json={
        "username": world.users["admin"]["username"], "password": PASSWORD})
    assert missing_mfa.status_code == 401 and missing_mfa.json()["detail"] == "MFA required"


def test_http_tenant_source_and_metadata_are_isolated(world):
    draft, _ = registered(world)
    foreign = world.headers["foreign"]
    assert world.client.get(BASE + "/" + draft["id"], headers=foreign).status_code == 404
    assert world.client.post(BASE, json=definition(draft["document_id"]), headers=foreign).status_code == 409
    assert world.client.post(BASE + "/" + draft["id"] + "/approve",
        json={"reason_code": "source_scope_complete"}, headers=foreign).status_code == 409
    with Session(world.engine) as db:
        assert db.get(ReferenceDatasetVersion, draft["id"]).status == "draft"


def test_http_rejects_dates_counts_scope_and_client_approval_flags(world):
    document_id, _ = uploaded(world)
    for change in ({"effective_until": "2026-01-01"}, {"coverage_until": "2026-01-01"},
                   {"expected_record_count": 2}, {"scope": {"all_services": False}}):
        response = world.client.post(BASE, json=definition(document_id, **change), headers=world.headers["admin"])
        assert response.status_code == 409, response.text
    for change in ({"status": "approved"}, {"approved_by": world.users["admin"]["id"]},
                   {"owner_organization_id": str(uuid4())}, {"expected_record_count": True},
                   {"version": "1"}, {"family": "inferred"}, {"amount": "100"}):
        response = world.client.post(BASE, json=definition(document_id, **change), headers=world.headers["admin"])
        assert response.status_code == 422, response.text
    with Session(world.engine) as db:
        assert db.scalar(select(ReferenceDatasetVersion.id)) is None


def test_http_source_change_blocks_approval_and_writer_cannot_read_metadata(world):
    document_id, _ = uploaded(world)
    response = world.client.post(BASE, json=definition(document_id), headers=world.headers["writer"])
    assert response.status_code == 201, response.text
    draft = response.json()
    with Session(world.engine) as db:
        row = db.scalar(select(ExtractedSourceRecord).where(ExtractedSourceRecord.job_id == draft["job_id"]))
        row.values = {**row.values, "payload": row.values["payload"].replace('"eligible": true', '"eligible": false')}
        db.commit()
    response = world.client.post(BASE + "/" + draft["id"] + "/approve",
        json={"reason_code": "source_scope_complete"}, headers=world.headers["admin"])
    assert response.status_code == 409 and "changed" in response.json()["detail"]
    assert world.client.get(BASE + "/" + draft["id"], headers=world.headers["writer"]).status_code == 403
    invalid_reason = world.client.post(BASE + "/" + draft["id"] + "/approve",
        json={"reason_code": "approve"}, headers=world.headers["admin"])
    assert invalid_reason.status_code == 422
