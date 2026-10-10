"""Deterministic, idempotent, held-only synthetic dataset with hash receipt."""
import hashlib, json
from datetime import date, timedelta
from decimal import Decimal
from importlib.resources import files
from uuid import UUID, uuid5
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import Session
from mcias.seed.schemas import Dataset
from mcias.models import Organization, User, Role, Permission, RolePermission, UserRole, SourceFile, AuditLog
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord
from mcias.models_claims import ClaimBatch, ClaimEntry
from mcias.reporting_g7 import create_snapshot
from mcias.security import hash_password
NAMESPACE = UUID("31233666-7a1d-44e1-a7d4-5a9725631a3f")

def identifier(label):
    return str(uuid5(NAMESPACE, "workspace-v1:" + label))

def load(config):
    config.validate()
    raw = files("mcias.seed").joinpath("data/workspace-v1.json").read_bytes()
    spec = Dataset.model_validate_json(raw)
    digest = hashlib.sha256(raw + str(config.count).encode()).hexdigest()
    engine = create_engine(config.database_url)
    try:
        with Session(engine, expire_on_commit=False) as db:
            db.execute(text("SELECT pg_advisory_xact_lock(31233666)"))
            org_id = identifier("organization")
            previous = db.scalar(select(AuditLog).where(AuditLog.action == "synthetic_seed_loaded", AuditLog.resource_id == org_id))
            if previous:
                if previous.details["dataset_sha256"] != digest:
                    raise ValueError("dataset changed; use a fresh dedicated test database")
                manifest = dict(previous.details["manifest"])
                manifest["password"] = "synthetic_e2e_password_only"
                actor = db.get(User, identifier("reader"))
                if db.scalar(select(func.count()).select_from(ClaimEntry).where(ClaimEntry.organization_id == org_id)) != config.count:
                    raise ValueError("seed receipt does not match current database")
                if config.count > 1000:
                    return manifest
                from mcias.models_reporting_g7 import ReportSnapshot
                report = db.scalar(select(ReportSnapshot).where(ReportSnapshot.batch_id == manifest["batch_id"]).order_by(ReportSnapshot.version.desc()))
                if report is None:
                    report = create_snapshot(db, actor, manifest["batch_id"])
                manifest.update(report_id=report.id, expected=report.summary)
                return manifest
            if db.get(Organization, org_id) or db.scalar(select(User.id).where(User.username == spec.username)):
                raise ValueError("unowned seed identity collision")
            org = Organization(id=org_id, name=spec.organization_name)
            outsider = Organization(id=identifier("foreign-organization"), name="SYN-E2E foreign scope")
            db.add_all([org, outsider]); db.flush()
            actor = User(id=identifier("reader"), organization_id=org.id, username=spec.username,
                         password_hash=hash_password("synthetic_e2e_password_only"))
            role = Role(id=identifier("reader-role"), code="SYN-workspace-reader")
            db.add_all([actor, role]); db.flush()
            db.add(UserRole(user_id=actor.id, role_id=role.id))
            for code in spec.permissions:
                permission = db.scalar(select(Permission).where(Permission.code == code))
                if permission is None:
                    permission = Permission(id=identifier("permission:" + code), code=code)
                    db.add(permission); db.flush()
                db.add(RolePermission(role_id=role.id, permission_id=permission.id))
            source = SourceFile(id=identifier("source"), sha256=digest,
                                original_filename="SYN-workspace.csv", storage_key="SYN-fixture-metadata-no-original")
            db.add(source); db.flush()
            doc = IngestionDocument(id=identifier("document"), organization_id=org.id,
                                    source_id=source.id, sha256=digest, filename=source.original_filename, status="extracted")
            db.add(doc); db.flush()
            job = IngestionJob(id=identifier("job"), organization_id=org.id, document_id=doc.id,
                               status="extracted", manifest={"complete": True, "synthetic_metadata_only": True})
            db.add(job); db.flush()
            batch = ClaimBatch(id=identifier("batch"), organization_id=org.id, ingestion_document_id=doc.id,
                created_by=actor.id, status="imported", source_sha256=digest,
                record_count=config.count, imported_count=config.count)
            db.add(batch); db.flush()
            ids = []
            for i in range(config.count):
                values = {"claim_reference": "SYN-E2E-" + str(i + 1), "claimed_amount": str(spec.claimed_amount),
                          "diagnosis": "SYNTHETIC_PRIVATE_FIELD_NOT_DISCLOSED"}
                record = ExtractedSourceRecord(id=identifier("record:" + str(i)), job_id=job.id,
                                               locator={"row": i + 2}, values=values)
                db.add(record); db.flush()
                claim = ClaimEntry(id=identifier("claim:" + str(i)), organization_id=org.id, batch_id=batch.id,
                    extracted_record_id=record.id, source_locator=record.locator, source_values=values,
                    claim_reference=values["claim_reference"], beneficiary_token="SYN-BEN-" + str(i % 1000),
                    provider_code="SYN-PROVIDER" if config.count == 12 else "SYN-PROVIDER-" + str(i % 100),
                    service_code="SYN-SERVICE", service_date=date(2026, 9, 1) + timedelta(days=i % 365),
                    claimed_amount=spec.claimed_amount, currency=spec.currency)
                db.add(claim); ids.append(claim.id)
                if i % 500 == 0: db.flush()
            db.flush()
            # Snapshot creation owns its commit. Receipt permits retry without duplicating data.
            manifest = {"username": actor.username, "password": "synthetic_e2e_password_only",
                        "organization_id": org.id, "claim_ids": ids, "batch_id": batch.id,
                        "seed_version": spec.version, "dataset_sha256": digest,
                        "source_original_available": False}
            db.add(AuditLog(actor_id=actor.id, action="synthetic_seed_loaded", resource_type="organization",
                           resource_id=org.id, details={"dataset_sha256": digest, "manifest": {k:v for k,v in manifest.items() if k != "password"}}))
            db.commit()
            if config.count > 1000:
                return manifest
            report = create_snapshot(db, actor, batch.id)
            manifest.update(report_id=report.id, expected=report.summary)
            return manifest
    finally:
        engine.dispose()
