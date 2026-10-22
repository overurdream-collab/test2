"""Native G2 sources + bounded G3 Super Admin completeness attestations.

Synthetic only. PostgreSQL cases use disposable per-test schemas, never production.
"""
from datetime import date
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace
from uuid import uuid4
import csv
import json
import os

import pytest
from sqlalchemy import create_engine, select, text, update, delete
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from mcias.models import Base, Organization, Permission, Role, RolePermission, User, UserRole, AuditLog, SourceFile
from mcias.models_ingestion import ExtractedSourceRecord, IngestionDocument
from mcias.models_reference import ReferenceDatasetVersion
from mcias.ingestion.orchestrator import ingest
from mcias.reference import ReferenceConflict
from mcias.reference_service import (register_reference_dataset, approve_reference_dataset,
    applicable_reference_snapshots, _dataset_payload)
from mcias.storage import EncryptedStore

START, END = date(2026, 1, 1), date(2027, 1, 1)
SCOPE = {"all_providers": True, "all_services": True, "all_beneficiaries": True}


def payload(family):
    data = {
        "beneficiary": dict(beneficiary_token="SYN-B1", employee_token="SYN-E1", relationship="child",
            category_code="SYN-C1", covered_services=["SYN-S1"], eligible=True),
        "contract": dict(provider_code="SYN-P1", contract_key="SYN-CONTRACT", covered_services=["SYN-S1"], excluded_services=[]),
        "tariff": dict(provider_code="SYN-P1", service_code="SYN-S1", category_code="SYN-C1", currency="USD",
            unit="service", unit_price="100.00", price_basis="unit_price", price_comparison="exact"),
        "policy": dict(service_code="SYN-S1", category_code="SYN-C1", currency="USD", copay_percent="20",
            requires_execution_evidence=True, minimum_dispense_interval_days=None, copay_basis="claimed_amount",
            rounding="HALF_UP", precision=2, duplicate_paid_claims_prohibited=True),
        "caps": dict(beneficiary_token="SYN-B1", category_code="SYN-C1", service_code="SYN-S1", currency="USD",
            limit_amount="1000", consumed_amount="200", period_from="2026-01-01", period_until="2027-01-01",
            consumption_as_of="2026-05-31", consumed_excludes_current_claim=True, consumption_basis="claimed_amount"),
        "history": dict(beneficiary_token="SYN-B1", provider_code="SYN-P1", service_code="SYN-S1",
            service_date="2026-01-01", claim_reference="SYN-PAST", paid=True, quantity="1", unit="service",
            amount="100", currency="USD", next_dispense_due_date=None),
    }[family]
    return {"effective_from": START.isoformat(), "effective_until": END.isoformat(), **data}


def csv_bytes(records):
    out = StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(["record_key", "payload"])
    for index, row in enumerate(records, 1):
        writer.writerow(["SYN-R" + str(index), json.dumps(row, sort_keys=True)])
    return out.getvalue().encode()


@pytest.fixture(params=["sqlite", "postgres"])
def world(request, tmp_path, monkeypatch):
    monkeypatch.setenv("MCIAS_ENVIRONMENT", "development")
    monkeypatch.setenv("MCIAS_MALWARE_SCAN", "disabled")
    url = "sqlite://" if request.param == "sqlite" else os.getenv("MCIAS_G3_REFERENCE_DATABASE_URL")
    if not url:
        pytest.skip("dedicated synthetic PG16 URL not supplied")
    engine = create_engine(url)
    schema = None
    if request.param == "postgres":
        assert engine.url.host in ("localhost", "127.0.0.1")
        assert engine.url.database.startswith("mcias_")
        with engine.begin() as connection:
            assert 160000 <= int(connection.scalar(text("SHOW server_version_num"))) < 170000
            schema = "g3_dataset_" + uuid4().hex
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        url = engine.url
        engine.dispose()
        engine = create_engine(url, connect_args={"options": "-csearch_path=" + schema})
        bound = engine.execution_options(schema_translate_map={None: schema})
    else:
        bound = engine
    Base.metadata.create_all(bound)
    if schema:
        # Exercise the actual additive migration and its database guard, not an ORM-only substitute.
        import runpy
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        with bound.begin() as connection:
            ReferenceDatasetVersion.__table__.drop(connection)
            with Operations.context(MigrationContext.configure(connection)):
                runpy.run_path("alembic/versions/0019_reference_dataset_v1.py")["upgrade"]()
    store = EncryptedStore(str(tmp_path / "source"), b"d" * 32)
    with Session(bound, expire_on_commit=False) as db:
        org = Organization(name="SYN-DATASETS")
        other = Organization(name="SYN-OTHER")
        db.add_all([org, other]); db.flush()
        admin = User(organization_id=org.id, username="SYN-admin-" + uuid4().hex, password_hash="unused")
        writer = User(organization_id=org.id, username="SYN-writer-" + uuid4().hex, password_hash="unused")
        outsider = User(organization_id=other.id, username="SYN-other-" + uuid4().hex, password_hash="unused")
        db.add_all([admin, writer, outsider]); db.flush()
        for actor, role_name, permission_code in ((admin, "super_admin", "workspace.super_admin"),
                (writer, "reference_writer", "reference.write"), (outsider, "other_admin", "reference.read")):
            role = Role(code=role_name)
            permission = Permission(code=permission_code)
            db.add_all([role, permission]); db.flush()
            db.add_all([UserRole(user_id=actor.id, role_id=role.id),
                RolePermission(role_id=role.id, permission_id=permission.id)])
        # A foreign writer has genuine server permission but cannot access this tenant's source.
        writer_role = db.scalar(select(Role).where(Role.code == "reference_writer"))
        db.add(UserRole(user_id=outsider.id, role_id=writer_role.id))
        db.commit()
        claim = SimpleNamespace(organization_id=org.id, beneficiary_token="SYN-B1", provider_code="SYN-P1",
            service_code="SYN-S1", service_date=date(2026, 6, 1), currency="USD")

        def register(family="beneficiary", rows=None, version=1, start=START, end=END, scope=None,
                count=None, document=None, actor=None, coverage_start=START, coverage_end=END):
            if document is None:
                raw = csv_bytes(rows if rows is not None else [payload(family)])
                result = ingest(db, store, org.id, admin.id, "SYN-reference.csv", raw)
                assert result["status"] in {"extracted", "duplicate"}
                document = result["document_id"]
                source = db.get(SourceFile, db.get(IngestionDocument, document).source_id)
                assert store.get(source.storage_key, source.sha256) == raw
            return register_reference_dataset(db, actor or admin, document, family, dataset_key="SYN-" + family,
                version=version, effective_from=start, effective_until=end, coverage_from=coverage_start,
                coverage_until=coverage_end, scope=scope or SCOPE,
                expected_record_count=count if count is not None else len(rows or [payload(family)]))

        yield SimpleNamespace(db=db, bound=bound, org=org, admin=admin, writer=writer, outsider=outsider,
            claim=claim, register=register, store=store)
    if schema:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


def test_all_six_native_sources_require_actual_super_admin_approval_and_survive_commit(world):
    ids = {}
    for family in ("beneficiary", "contract", "tariff", "policy", "caps", "history"):
        item = world.register(family)
        before = next(c for c in applicable_reference_snapshots(world.db, world.claim) if c["family"] == family)
        assert not before["complete"] and before["lookup_status"] == "reference_unapproved"
        approved = approve_reference_dataset(world.db, world.admin, item.id, reason_code="source_scope_complete")
        ids[family] = approved.id
        assert approve_reference_dataset(world.db, world.admin, item.id, reason_code="source_scope_complete").approval_event_id == approved.approval_event_id
    with Session(world.bound) as independent:
        certificates = applicable_reference_snapshots(independent, world.claim)
        assert len(certificates) == 6
        for cert in certificates:
            assert cert["reference_id"] == ids[cert["family"]]
            assert cert["complete"] and cert["approved"] and cert["lookup_complete"]
            assert cert["version"] == 1 and cert["owner_organization_id"] == world.org.id
            assert cert["completeness_basis"] == "SUPER_ADMIN_SOURCE_SCOPE_ATTESTATION"
            assert cert["observed_record_count"] == cert["expected_record_count"] == 1
            assert cert["records"][0]["locator"]["row"] == 2
            assert len(cert["source_evidence"][0]["source_sha256"]) == 64
            assert independent.get(AuditLog, cert["approval_event_id"]).actor_id == world.admin.id
        assert len(independent.scalars(select(AuditLog).where(AuditLog.action == "reference_dataset_approved")).all()) == 6


def test_historical_dataset_selection_does_not_take_newer_version(world):
    old = world.register("tariff", end=date(2026, 7, 1))
    approve_reference_dataset(world.db, world.admin, old.id, reason_code="source_scope_complete")
    future_payload = payload("tariff")
    future_payload.update(unit_price="300", effective_from="2026-07-01")
    newer = world.register("tariff", rows=[future_payload], version=2, start=date(2026, 7, 1))
    approve_reference_dataset(world.db, world.admin, newer.id, reason_code="source_scope_complete")
    cert = next(c for c in applicable_reference_snapshots(world.db, world.claim) if c["family"] == "tariff")
    assert cert["reference_id"] == old.id and cert["version"] == 1
    assert Decimal(cert["records"][0]["values"]["unit_price"]) == Decimal("100")
    world.claim.service_date = date(2026, 7, 1)
    cert = next(c for c in applicable_reference_snapshots(world.db, world.claim) if c["family"] == "tariff")
    assert cert["reference_id"] == newer.id and cert["version"] == 2


def test_permissions_scope_counts_and_foreign_ownership_fail_closed(world):
    item = world.register()
    with pytest.raises(ReferenceConflict, match="Super Admin"):
        approve_reference_dataset(world.db, world.writer, item.id, reason_code="source_scope_complete")
    with pytest.raises(ReferenceConflict, match="accessible"):
        world.register(document=item.document_id, actor=world.outsider)
    with pytest.raises(ReferenceConflict, match="control total"):
        world.register(count=2)
    with pytest.raises(ReferenceConflict, match="explicit source scope"):
        approve_reference_dataset(world.db, world.admin, item.id, reason_code="approved")
    assert world.db.get(ReferenceDatasetVersion, item.id).status == "draft"


def test_source_tamper_and_uncovered_date_never_become_complete(world):
    item = world.register(coverage_end=date(2026, 6, 1))
    approve_reference_dataset(world.db, world.admin, item.id, reason_code="source_scope_complete")
    cert = next(c for c in applicable_reference_snapshots(world.db, world.claim) if c["family"] == "beneficiary")
    assert not cert["complete"] and cert["lookup_status"] == "reference_not_effective"
    world.claim.service_date = date(2026, 5, 1)
    record = world.db.scalar(select(ExtractedSourceRecord).where(ExtractedSourceRecord.job_id == item.job_id))
    value = payload("beneficiary"); value["eligible"] = False
    record.values = {"record_key": "SYN-R1", "payload": json.dumps(value)}
    world.db.commit()
    with Session(world.bound) as independent:
        cert = next(c for c in applicable_reference_snapshots(independent, world.claim) if c["family"] == "beneficiary")
        assert not cert["complete"] and cert["lookup_status"] == "reference_incomplete"
        assert cert["gaps"] == ["source_hash_invalid"]


def test_approved_metadata_is_immutable_and_overlap_is_rejected(world):
    item = world.register()
    approve_reference_dataset(world.db, world.admin, item.id, reason_code="source_scope_complete")
    item.scope = {"all_beneficiaries": False}
    with pytest.raises(ValueError, match="immutable"):
        world.db.commit()
    world.db.rollback()
    overlap = world.register(version=2)
    with pytest.raises(ReferenceConflict, match="overlap"):
        approve_reference_dataset(world.db, world.admin, overlap.id, reason_code="source_scope_complete")


def test_declared_scope_is_bounded_and_foreign_claims_never_gain_completeness(world):
    with pytest.raises(ReferenceConflict, match="scope"):
        world.register(scope={"category_code": "SYN-C1"})
    with pytest.raises(ReferenceConflict, match="scope"):
        world.register(scope={"all_services": False})
    item = world.register(scope={"provider_code": "SYN-P1", "beneficiary_token": "SYN-B1"})
    approve_reference_dataset(world.db, world.admin, item.id, reason_code="source_scope_complete")
    world.claim.beneficiary_token = "SYN-OUTSIDE"
    assert not next(c for c in applicable_reference_snapshots(world.db, world.claim) if c["family"] == "beneficiary")["complete"]
    world.claim.organization_id = world.outsider.organization_id
    assert not any(c["complete"] for c in applicable_reference_snapshots(world.db, world.claim))


def test_postgres_migration_guard_blocks_sql_mutation_and_unauthorized_approval(world):
    if world.bound.dialect.name != "postgresql":
        pytest.skip("database trigger is PostgreSQL-specific")
    item = world.register()
    approve_reference_dataset(world.db, world.admin, item.id, reason_code="source_scope_complete")
    for statement in (update(ReferenceDatasetVersion).where(ReferenceDatasetVersion.id == item.id).values(version=42),
                      delete(ReferenceDatasetVersion).where(ReferenceDatasetVersion.id == item.id)):
        with pytest.raises(DBAPIError, match="immutable"):
            world.db.execute(statement)
        world.db.rollback()
    draft = world.register("policy")
    from mcias.audit_writer import write_event
    event = write_event(world.db, actor=world.writer, organization_id=world.org.id,
        action="reference_dataset_approved", resource_type="reference_dataset_version", resource_id=draft.id,
        outcome="success")
    with pytest.raises(DBAPIError, match="not authorized"):
        world.db.execute(update(ReferenceDatasetVersion).where(ReferenceDatasetVersion.id == draft.id)
            .values(status="approved", approved_by=world.writer.id, approved_at=world.admin.created_at,
                    approval_event_id=event.id))
    world.db.rollback()


@pytest.mark.parametrize("family,key,value", [
    ("tariff", "price_basis", "invoice_total"),
    ("tariff", "unit_price", 100.0),
    ("tariff", "price_comparison", "guessed_ceiling"),
    ("policy", "copay_percent", "101"),
    ("policy", "covered_services", ["SYN-S1"]),
    ("caps", "consumption_as_of", "not-a-date"),
    ("caps", "consumption_as_of", "2025-12-31"),
    ("beneficiary", "covered_services", [{}]),
])
def test_unqualified_source_payload_rejected(family, key, value):
    row = payload(family); row[key] = value
    with pytest.raises(ReferenceConflict):
        _dataset_payload(family, json.dumps(row))
