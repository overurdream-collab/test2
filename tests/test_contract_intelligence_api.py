"""Contract Intelligence HTTP is tenant-scoped and preview-only (synthetic data)."""
from hashlib import sha256
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from mcias.app import app, get_db
from mcias.models import Base, Organization, User, Role, Permission, UserRole, RolePermission, SourceFile
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord
from mcias.models_reference_points import ReferencePoint
import mcias.contract_intelligence_api as contract_api


@pytest.fixture
def client_fixture(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        home, other = Organization(name="SYN-contract"), Organization(name="SYN-other")
        db.add_all([home, other]); db.flush()
        editor = User(username="SYN-contract-editor", password_hash="unusable", organization_id=home.id)
        reader = User(username="SYN-contract-viewer", password_hash="unusable", organization_id=home.id)
        foreign = User(username="SYN-contract-foreign", password_hash="unusable", organization_id=other.id)
        db.add_all([editor, reader, foreign]); db.flush()
        role = Role(code="SYN-contract-editor-role")
        role_reader = Role(code="SYN-contract-readonly-role")
        db.add_all([role, role_reader]); db.flush()
        for code in ("reference.write", "workspace.super_admin", "medical_fields.text.read"):
            permission = Permission(code=code)
            db.add(permission); db.flush()
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        p = Permission(code="reference.read")
        db.add(p); db.flush()
        db.add(RolePermission(role_id=role_reader.id, permission_id=p.id))
        db.add_all([UserRole(user_id=editor.id, role_id=role.id),
                    UserRole(user_id=reader.id, role_id=role_reader.id),
                    UserRole(user_id=foreign.id, role_id=role.id)])
        db.flush()
        source = SourceFile(sha256=sha256(b"SYN-contract").hexdigest(),
                            original_filename="SYN-contract.pdf", storage_key="SYN-storage-only")
        db.add(source); db.flush()
        doc = IngestionDocument(organization_id=home.id, source_id=source.id,
                                sha256=source.sha256, filename="SYN-contract.pdf", status="extracted")
        db.add(doc); db.flush()
        job = IngestionJob(organization_id=home.id, document_id=doc.id,
                           status="extracted", manifest={"complete": True})
        db.add(job); db.flush()
        record = ExtractedSourceRecord(
            job_id=job.id, locator={"kind": "page", "index": 1, "row": None, "column": None},
            values={"text": "H1 CONSULT price 5000 YER effective 2026-01-01"}, confidence=100)
        db.add(record); db.commit()
        ids = {"editor": editor.id, "reader": reader.id, "foreign": foreign.id,
               "document": doc.id, "record": record.id, "job": job.id, "home": home.id}

    def get_test_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = get_test_db
    monkeypatch.setattr(contract_api, "resolve_user", lambda db, auth:
        (db.get(User, ids[auth.replace("Bearer ", "")]), None))
    monkeypatch.setenv("MCIAS_CONTRACT_LLM_URL", "http://127.0.0.1:23456/v1/chat/completions")
    monkeypatch.setenv("MCIAS_CONTRACT_LLM_MODEL", "SYN-model")
    monkeypatch.setenv("MCIAS_CONTRACT_LLM_REVISION", "SYN-revision")
    def fake_model(blocks, **kwargs):
        return {"candidates": [{
            "record_id": ids["record"], "quote": "H1 CONSULT price 5000 YER effective 2026-01-01",
            "section": "tariffs", "logical_key": "H1:CONSULT", "provider_code": "H1",
            "service_code": "CONSULT", "currency": "YER", "rule_type": "amount",
            "amount": "5000", "effective_from": "2026-01-01", "effective_until": None,
            "status": "APPROVED"}],
            "request_sha256": "SYN-request-hash", "response_sha256": "SYN-response-hash"}
    monkeypatch.setattr(contract_api, "infer_local", fake_model)
    try:
        yield TestClient(app), ids, engine
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def request(client, ids, who="editor", document=None):
    return client.post("/api/v1/contract-intelligence/documents/" +
                       (document or ids["document"]) + "/preview",
                       headers={"Authorization": "Bearer " + who})


def test_preview_returns_proposals_without_mutating_financial_records(client_fixture):
    client, ids, engine = client_fixture
    res = request(client, ids)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PREVIEW_ONLY"
    assert data["model_id"] == "SYN-model"
    assert data["clauses"][0]["status"] == "DRAFT_ONLY"
    assert data["clauses"][0]["source_locator"]["index"] == 1
    with Session(engine) as db:
        assert db.query(ReferencePoint).count() == 0


def test_read_only_user_has_no_access_to_model_or_source(client_fixture):
    client, ids, _ = client_fixture
    assert request(client, ids, who="reader").status_code == 403


def test_foreign_tenant_cannot_preview_home_document(client_fixture):
    client, ids, _ = client_fixture
    assert request(client, ids, who="foreign").status_code == 404


def test_quarantined_document_is_rejected(client_fixture):
    client, ids, engine = client_fixture
    with Session(engine) as db:
        doc = db.get(IngestionDocument, ids["document"])
        doc.status = "review_required"
        db.commit()
    assert request(client, ids).status_code == 409


def test_disabled_model_fails_closed(client_fixture, monkeypatch):
    client, ids, _ = client_fixture
    monkeypatch.delenv("MCIAS_CONTRACT_LLM_URL")
    assert request(client, ids).status_code == 503


def test_ocr_uncertain_never_verified(client_fixture):
    client, ids, engine = client_fixture
    with Session(engine) as db:
        rec = db.get(ExtractedSourceRecord, ids["record"])
        rec.confidence = 50
        db.commit()
    res = request(client, ids)
    assert res.status_code == 200
    assert res.json()["clauses"][0]["evidence_status"] == "needs_human_review"
    assert "ocr_uncertain" in res.json()["clauses"][0]["validation_errors"]


def test_missing_sensitive_field_permission_denied(client_fixture):
    client, ids, engine = client_fixture
    with Session(engine) as db:
        rec = db.get(ExtractedSourceRecord, ids["record"])
        rec.values = {"private_diagnosis": "SYN", "text": rec.values["text"]}
        db.commit()
    assert request(client, ids).status_code == 403
