"""Bounded reference evidence against native committed G3 records."""
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
import json
import os
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, SourceFile, WrittenAuthorization
from mcias.models_reference import ContractVersion, ProviderTariff
from mcias.production_authorization import signed_payload
from mcias.reference_service import REFERENCE_FAMILIES, applicable_reference_snapshots


@pytest.fixture(params=("sqlite", "postgres"))
def engine(request):
    if request.param == "sqlite":
        engine = create_engine("sqlite+pysqlite:///:memory:")
    else:
        url = os.getenv("MCIAS_G3_REFERENCE_DATABASE_URL")
        if not url:
            pytest.skip("isolated PostgreSQL16 URL not configured")
        parsed = make_url(url)
        assert parsed.host in ("127.0.0.1", "localhost", "::1")
        assert parsed.database == "mcias_inputs_g3"
        engine = create_engine(url)
        with engine.connect() as connection:
            assert 160000 <= int(connection.scalar(text("SHOW server_version_num"))) < 170000
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def seed(db, tmp_path, monkeypatch):
    organization = Organization(name="SYN-G3")
    db.add(organization); db.flush()
    approver = User(organization_id=organization.id, username="SYN-" + str(uuid4()), password_hash="synthetic")
    db.add(approver)
    source = SourceFile(sha256="a" * 64, original_filename="SYN-approved.pdf", storage_key="SYN/" + str(uuid4()))
    db.add(source); db.flush()
    old = ContractVersion(organization_id=organization.id, provider_code="SYN-P", version=1,
        effective_from=date(2026, 1, 1), effective_until=date(2026, 6, 1), status="approved")
    new = ContractVersion(organization_id=organization.id, provider_code="SYN-P", version=2,
        effective_from=date(2026, 6, 1), effective_until=date(2027, 1, 1), status="approved")
    db.add_all([old, new]); db.flush()
    approvals = []
    # Distinct authorization IDs let the existing signed-registry representation
    # bind both historical versions independently without inventing a new store.
    for contract in (old, new):
        approval = WrittenAuthorization(organization_id=organization.id, source_id=source.id,
            approved_by=approver.id, approved_at=datetime(2025, 12, 1, tzinfo=timezone.utc))
        db.add(approval); db.flush()
        contract.authorization_id = approval.id
        approvals.append(approval)
    tariff = ProviderTariff(contract_id=old.id, service_code="SYN-S", amount=Decimal("100"), currency="SAR")
    db.add(tariff)
    db.add(ProviderTariff(contract_id=new.id, service_code="SYN-S", amount=Decimal("120"), currency="SAR"))
    db.commit()
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    registry = {"approvals": {}, "trusted_heads": {organization.id: {approver.id: public}}}
    for contract, approval in zip((old, new), approvals):
        registry["approvals"][approval.id] = {"rule_id": contract.id, "authorization_id": approval.id,
            "signature": private.sign(signed_payload(contract, approval, source)).hex()}
    path = tmp_path / "synthetic-reference-trust.json"
    path.write_text(json.dumps(registry)); path.chmod(0o600)
    monkeypatch.setenv("MCIAS_AUTHORIZATION_REGISTRY", str(path))
    claim = SimpleNamespace(organization_id=organization.id, beneficiary_token="SYN-private-token",
        provider_code="SYN-P", service_code="SYN-S", service_date=date(2026, 2, 1), currency="SAR")
    return claim, old.id, new.id, tariff.id, source.id, path


def lookup(db, claim, policy=None):
    return {item["family"]: item for item in applicable_reference_snapshots(db, claim, policy)}


def test_committed_historical_version_despite_newer_version(engine, tmp_path, monkeypatch):
    with Session(engine) as db:
        claim, old_id, newer_id, tariff_id, source_id, _ = seed(db, tmp_path, monkeypatch)
    with Session(engine) as db:
        result = lookup(db, claim)
        assert tuple(result) == tuple(family for family, _ in REFERENCE_FAMILIES)
        assert len(result) == 6
        assert result["contract"]["reference_id"] == old_id
        assert result["contract"]["reference_id"] != newer_id
        assert result["contract"]["version"] == 1
        assert result["tariff"]["reference_id"] == tariff_id
        assert result["tariff"]["lookup_complete"] is True
        assert result["tariff"]["approved"] is True
        assert result["tariff"]["source_evidence"][0]["source_id"] == source_id
        assert result["tariff"]["source_evidence"][0]["source_sha256"] == "a" * 64
        assert all(item["complete"] is False for item in result.values())
        assert "SYN-private-token" not in json.dumps(result)
        claim.service_date = date(2026, 6, 1)
        assert lookup(db, claim)["contract"]["reference_id"] == newer_id


def test_missing_reference_cannot_prove_violation(engine, tmp_path, monkeypatch):
    with Session(engine) as db:
        claim, *_ = seed(db, tmp_path, monkeypatch)
        result = lookup(db, claim, SimpleNamespace(approved=True, policy_id="unverified"))
        assert result["beneficiary"]["reference_id"] is None
        assert result["beneficiary"]["lookup_complete"] is False
        assert "reference_missing" in result["beneficiary"]["gaps"]
        assert result["policy"]["approved"] is False
        assert result["caps"]["complete"] is False
        assert result["history"]["complete"] is False
        assert result["history"]["observed_record_ids"] == []
        assert all(item["lookup_status"] != "reference_proven_violation" for item in result.values())


def test_unsigned_or_tampered_source_cannot_attest_tariff(engine, tmp_path, monkeypatch):
    with Session(engine) as db:
        claim, _, _, _, source_id, path = seed(db, tmp_path, monkeypatch)
        monkeypatch.delenv("MCIAS_AUTHORIZATION_REGISTRY")
        assert lookup(db, claim)["tariff"]["lookup_complete"] is False
        monkeypatch.setenv("MCIAS_AUTHORIZATION_REGISTRY", str(path))
        source = db.get(SourceFile, source_id)
        source.sha256 = "b" * 64
        db.commit()
        result = lookup(db, claim)
        assert result["contract"]["approved"] is False
        assert result["tariff"]["lookup_complete"] is False
        assert "authorization_invalid" in result["contract"]["gaps"]


def test_expiry_tenant_isolation_and_unrelated_transaction(engine, tmp_path, monkeypatch):
    with Session(engine) as db:
        claim, *_ = seed(db, tmp_path, monkeypatch)
        claim.service_date = date(2027, 1, 1)
        assert lookup(db, claim)["contract"]["lookup_status"] == "reference_not_effective"
        claim.organization_id = str(uuid4())
        assert lookup(db, claim)["contract"]["reference_id"] is None
        pending = Organization(name="SYN-must-not-commit")
        db.add(pending)
        lookup(db, claim)
        pending_id = pending.id
        db.rollback()
    with Session(engine) as db:
        assert db.get(Organization, pending_id) is None
