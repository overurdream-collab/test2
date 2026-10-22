"""Bounded, synthetic, native G2 -> G6 measurement. Never an importer or SLA.

Each size runs in a fresh process and a disposable PG16 schema. Only the
existing services create claims, reference certificates, snapshots and events.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, timezone
from hashlib import sha256
from io import BytesIO, StringIO
import csv
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

from sqlalchemy.engine import make_url


SIZES = (10, 25, 100)
FAMILIES = ("beneficiary", "contract", "tariff", "policy", "caps", "history")
DATABASE = "mcias_benchmark_inputs"


def validate_target(url, allow, sizes, max_seconds):
    """No database operation is permitted before this fail-closed guard."""
    if allow != "YES":
        raise ValueError("MCIAS_BENCHMARK_ALLOW=YES required")
    try:
        parsed = make_url(url)
    except Exception as exc:
        raise ValueError("invalid benchmark database URL") from exc
    if (parsed.drivername != "postgresql+psycopg"
        or parsed.host not in {"127.0.0.1", "localhost", "::1"}
        or parsed.database != DATABASE or not parsed.username or not parsed.password
        or parsed.query):
        raise ValueError("explicit local psycopg benchmark database required; no URL query options")
    if (not sizes or any(type(size) is not int or size not in SIZES for size in sizes)
        or len(set(sizes)) != len(sizes) or list(sizes) != sorted(sizes)):
        raise ValueError("sizes must be an increasing unique subset of 10,25,100")
    if type(max_seconds) is not int or not 15 <= max_seconds <= 300:
        raise ValueError("sample deadline must be 15..300 seconds")
    return parsed


def ratios(numerator, denominator):
    if denominator <= 0 or not 0 <= numerator <= denominator:
        raise ValueError("invalid measured ratio")
    return {"numerator": numerator, "denominator": denominator,
            "fraction": numerator / denominator}


def timing_partition(total, inspection, references):
    """Nested inclusive timings partition one real G5 call; do not add twice."""
    if not 0 <= references <= inspection <= total:
        raise ValueError("invalid nested timing")
    return {"g5_total_seconds": total, "reference_seconds": references,
            "rules_and_source_validation_seconds": inspection - references,
            "persistence_and_orchestration_seconds": total - inspection,
            "inspection_inclusive_seconds": inspection}


def synthetic_rows(size):
    if type(size) is not int or size not in SIZES:
        raise ValueError("unapproved sample size")
    return [{"claim_reference": f"SYN-CLAIM-{i:04d}", "beneficiary_token": f"SYN-BEN-{i:04d}",
        "provider_code": "SYN-PROVIDER", "service_code": "SYN-SERVICE", "service_date": "2026-06-01",
        "claimed_amount": "100", "currency": "USD", "quantity": "1", "unit_price": "100",
        "unit": "UNIT", "copay_amount": "20"} for i in range(size)]


def workbook_bytes(rows):
    from openpyxl import Workbook
    book = Workbook()
    sheet = book.active
    sheet.title = "CLAIMS"
    sheet.append(list(rows[0]))
    for row in rows:
        sheet.append(list(row.values()))
    payment = book.create_sheet("PAYMENT")
    payment.append(list(rows[0]))
    payment.append(["SYN-PAYMENT" if key == "claim_reference" else value
                    for key, value in rows[0].items()])
    stream = BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


def csv_bytes(rows):
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def reference_rows(rows):
    """Source facts only. G3 alone registers, approves and certifies them."""
    values = {
        "beneficiary": [{"beneficiary_token": r["beneficiary_token"], "employee_token": f"SYN-EMP-{i:04d}",
            "relationship": "self", "category_code": "SYN-CAT", "eligible": True,
            "covered_services": ["SYN-SERVICE"]} for i, r in enumerate(rows)],
        "contract": [{"provider_code": "SYN-PROVIDER", "contract_key": "SYN-CONTRACT",
            "covered_services": ["SYN-SERVICE"], "excluded_services": []}],
        "tariff": [{"provider_code": "SYN-PROVIDER", "service_code": "SYN-SERVICE", "category_code": "SYN-CAT",
            "currency": "USD", "unit": "UNIT", "unit_price": "100", "price_basis": "unit_price", "price_comparison": "exact"}],
        "policy": [{"service_code": "SYN-SERVICE", "category_code": "SYN-CAT", "currency": "USD", "copay_percent": "20",
            "requires_execution_evidence": True, "minimum_dispense_interval_days": 30,
            "copay_basis": "claimed_amount", "rounding": "HALF_UP", "precision": 2,
            "duplicate_paid_claims_prohibited": True, "early_dispense_days": 2}],
        "caps": [{"beneficiary_token": r["beneficiary_token"], "category_code": "SYN-CAT", "service_code": "SYN-SERVICE",
            "currency": "USD", "limit_amount": "1000", "consumed_amount": "0", "period_from": "2026-01-01",
            "period_until": "2026-07-01", "consumption_as_of": "2026-06-01", "consumed_excludes_current_claim": True,
            "consumption_basis": "claimed_amount"} for r in rows],
        # Different service, independently scoped beneficiaries: target-service consumption is zero.
        "history": [{"beneficiary_token": r["beneficiary_token"], "provider_code": "SYN-PROVIDER",
            "service_code": "SYN-OTHER", "service_date": "2026-05-01", "claim_reference": f"SYN-OLD-{i:04d}",
            "paid": True, "quantity": "1", "unit": "UNIT", "amount": "100", "currency": "USD"}
            for i, r in enumerate(rows)],
    }
    return {family: [{"record_key": f"SYN-{family}-{i:04d}", "payload": json.dumps({**value,
        "effective_from": "2026-01-01", "effective_until": "2026-07-01"}, sort_keys=True)}
        for i, value in enumerate(values[family])] for family in FAMILIES}


class Measurements:
    def __init__(self):
        self.seconds = Counter()
        self.calls = Counter()
        self.work_counts = Counter()
        self.stage = "setup"
        self.failure_stage = None

    @contextmanager
    def measure(self, name):
        previous = self.stage
        self.stage = name
        start = time.perf_counter()
        try:
            yield
        except Exception:
            if self.failure_stage is None:
                self.failure_stage = self.stage
            raise
        finally:
            self.seconds[name] += time.perf_counter() - start
            self.calls[name] += 1
            self.stage = previous


@contextmanager
def instrument(measurements):
    """Observe actual calls once; neither fabricated results nor service edits."""
    from unittest.mock import patch
    from mcias import audit_service, reference_service, claim_batches
    actual_inspect = audit_service.inspect_claim
    actual_references = reference_service.applicable_reference_snapshots
    actual_scope = claim_batches.source_scope

    def inspect(*args, **kwargs):
        with measurements.measure("inspection_inclusive"):
            return actual_inspect(*args, **kwargs)

    def references(*args, **kwargs):
        with measurements.measure("reference_lookup_inclusive"):
            result = actual_references(*args, **kwargs)
        measurements.work_counts["reference_certificate_rows_returned"] += sum(
            len(certificate.get("records", [])) for certificate in result)
        return result

    def scope(*args, **kwargs):
        result = actual_scope(*args, **kwargs)
        measurements.work_counts["claims_scope_rows_validated"] += result["source_records"]
        return result

    with patch.object(audit_service, "inspect_claim", inspect), patch.object(
        reference_service, "applicable_reference_snapshots", references), patch.object(
        claim_batches, "source_scope", scope):
        yield


def _run_sample(size, url, measurements, root, max_seconds):
    from sqlalchemy import create_engine, func, select, text
    from sqlalchemy.orm import Session
    from mcias import audit_service
    from mcias.claim_batches import approve_source_scope, attach, stage, resume
    from mcias.governance_g6 import open_case, append_event
    from mcias.ingestion.orchestrator import ingest
    from mcias.models import Base, AuditLog, Organization, Permission, Role, RolePermission, SourceFile, User, UserRole
    from mcias.models_audit import AuditSnapshot
    from mcias.models_claims import ClaimBatch, ClaimEntry
    from mcias.models_governance_g6 import GovernanceCase, GovernanceEvent
    from mcias.models_ingestion import ExtractedSourceRecord, IngestionDocument, IngestionJob, QuarantineItem
    from mcias.reference_service import register_reference_dataset, approve_reference_dataset
    from mcias.storage import EncryptedStore

    rows = synthetic_rows(size)
    sources = []
    trace = []
    schema = "bench_inputs_" + uuid4().hex
    engine = create_engine(url, connect_args={"connect_timeout": 3,
        "options": "-c statement_timeout=20000 -c lock_timeout=3000"})
    created = False
    start = time.perf_counter()
    cpu_start = time.process_time()
    child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {"size": size, "expected_state": "MATCH_VERIFIED", "schema": schema,
              "measurement_status": "FAILED", "concurrency": 1, "sample_deadline_seconds": max_seconds}

    def ingest_source(db, actor, store, filename, data):
        with measurements.measure("g2_ingest_all_sources"):
            received = ingest(db, store, actor.organization_id, actor.id, filename, data)
        if received["status"] != "extracted":
            raise AssertionError("synthetic source did not extract")
        document = db.get(IngestionDocument, received["document_id"])
        source = db.get(SourceFile, document.source_id)
        with measurements.measure("encrypted_original_readback"):
            if store.get(source.storage_key, source.sha256) != data or source.sha256 != sha256(data).hexdigest():
                raise AssertionError("encrypted original digest/readback mismatch")
        count = db.scalar(select(func.count()).select_from(ExtractedSourceRecord).join(IngestionJob).where(
            IngestionJob.document_id == document.id))
        sources.append({"document_id": document.id, "sha256": document.sha256,
            "filename": filename, "bytes": len(data), "records": count, "encrypted_original_verified": True})
        return document

    def counts(db):
        return {"documents": db.scalar(select(func.count()).select_from(IngestionDocument)),
            "claims": db.scalar(select(func.count()).select_from(ClaimEntry)),
            "snapshots": db.scalar(select(func.count()).select_from(AuditSnapshot)),
            "claim_audit_events": db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "claim_inputs_audited")),
            "cases": db.scalar(select(func.count()).select_from(GovernanceCase)),
            "holds": db.scalar(select(func.count()).select_from(GovernanceEvent).where(GovernanceEvent.kind == "hold"))}

    try:
        with engine.begin() as connection:
            version = int(connection.scalar(text("SHOW server_version_num")))
            if not 160000 <= version < 170000:
                raise ValueError("PostgreSQL 16 required")
            result["postgres_version_num"] = version
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            created = True
        isolated = engine.execution_options(schema_translate_map={None: schema})
        with measurements.measure("schema_setup"):
            Base.metadata.create_all(isolated)
        store = EncryptedStore(str(root / "encrypted"), os.urandom(32))
        with Session(isolated, expire_on_commit=False) as db:
            org = Organization(name="SYN-NATIVE-BENCH")
            db.add(org)
            db.flush()
            actor = User(organization_id=org.id, username="SYN-" + uuid4().hex, password_hash="synthetic")
            role = Role(code="super_admin")
            db.add_all([actor, role])
            db.flush()
            db.add(UserRole(user_id=actor.id, role_id=role.id))
            for code in ("claims.read", "claims.import", "workspace.super_admin", "governance.review"):
                permission = Permission(code=code)
                db.add(permission)
                db.flush()
                db.add(RolePermission(role_id=role.id, permission_id=permission.id))
            db.commit()
            pipeline_start = time.perf_counter()
            original = workbook_bytes(rows)
            before = measurements.seconds["g2_ingest_all_sources"]
            document = ingest_source(db, actor, store, "SYN-claims.xlsx", original)
            result["g2_claim_workbook_ingest_seconds"] = measurements.seconds["g2_ingest_all_sources"] - before
            with measurements.measure("g4_approve_normalize"):
                approve_source_scope(db, actor, document.id, {1: "CLAIMS", 2: "PAYMENT"})
                batch = stage(db, actor, document.id)
                for chunk in range((size + 24) // 25):
                    normalized = resume(db, actor, batch.id, chunk_size=25)
                    if normalized["status"] == "imported":
                        break
                if normalized["status"] != "imported":
                    raise AssertionError("bounded normalization stalled")
            claims = sorted(db.scalars(select(ClaimEntry)).all(), key=lambda claim: claim.source_locator["row"])
            if len(claims) != size or any(claim.claim_reference == "SYN-PAYMENT" for claim in claims):
                raise AssertionError("claim count/payment exclusion mismatch")
            result["normalize_calls"] = chunk + 1
            with measurements.measure("g3_reference_source_setup"):
                for family, records in reference_rows(rows).items():
                    ref_doc = ingest_source(db, actor, store, "SYN-" + family + ".csv", csv_bytes(records))
                    item = register_reference_dataset(db, actor, ref_doc.id, family, dataset_key="SYN-" + family,
                        version=1, effective_from=date(2026, 1, 1), effective_until=date(2026, 7, 1),
                        coverage_from=date(2026, 1, 1), coverage_until=date(2026, 7, 1),
                        scope={"provider_code": "SYN-PROVIDER", "all_beneficiaries": True, "all_services": True},
                        expected_record_count=len(records))
                    approve_reference_dataset(db, actor, item.id, reason_code="source_scope_complete")
            executions = [{"evidence_kind": "service_execution", "claim_reference": row["claim_reference"],
                "beneficiary_token": row["beneficiary_token"], "provider_code": row["provider_code"],
                "service_code": row["service_code"], "service_date": row["service_date"], "unit": "UNIT",
                "performed_quantity": "1", "dose_status": "clear"} for row in rows]
            with measurements.measure("execution_source_and_attachment_setup"):
                execution_doc = ingest_source(db, actor, store, "SYN-execution.csv", csv_bytes(executions))
                for claim in claims:
                    attach(db, actor, claim.id, execution_doc.id)
            with instrument(measurements):
                for claim in claims:
                    with measurements.measure("g5_audit_and_shared_event"):
                        snapshot = audit_service.run_audit(db, actor, claim.id, review_only=True)
                    with measurements.measure("g6_case_and_hold"):
                        case = open_case(db, actor, snapshot.id)
                        hold = append_event(db, actor, case.id, "hold", {"reason_code": "advisory_human_review"})
                    trace.append({"claim_id": claim.id, "snapshot_id": snapshot.id,
                        "case_id": case.id, "hold_event_id": hold.id})
            result["pipeline_wall_seconds"] = time.perf_counter() - pipeline_start
            initial_counts = counts(db)
            with measurements.measure("reimport_and_retry"):
                duplicate = ingest(db, store, actor.organization_id, actor.id, "SYN-claims.xlsx", original)
                if duplicate["status"] != "duplicate" or duplicate["document_id"] != document.id:
                    raise AssertionError("reimport source deduplication failed")
                if stage(db, actor, document.id).id != batch.id or resume(db, actor, batch.id)["status"] != "imported":
                    raise AssertionError("reimport batch deduplication failed")
                for record in (trace[0], trace[-1]):
                    repeated = audit_service.run_audit(db, actor, record["claim_id"], review_only=True)
                    if repeated.id != record["snapshot_id"] or open_case(db, actor, repeated.id).id != record["case_id"]:
                        raise AssertionError("result/case retry deduplication failed")
            db.commit()
            result["retry"] = {"file_reimports": 1, "audit_retries": 2, "case_open_retries": 2,
                "counts_before": initial_counts, "counts_after": counts(db)}
            if result["retry"]["counts_before"] != result["retry"]["counts_after"]:
                raise AssertionError("retry increased durable counts")
            actor_id, org_id, document_id = actor.id, org.id, document.id
        # All assertions below read committed rows using a separate SQLAlchemy Session.
        with Session(isolated) as reread, measurements.measure("postcommit_validation"):
            durable_counts = counts(reread)
            expected_counts = {"documents": 8, "claims": size, "snapshots": size,
                "claim_audit_events": size, "cases": size, "holds": size}
            if durable_counts != expected_counts:
                raise AssertionError("postcommit count mismatch")
            outcomes = Counter()
            completed_refs = evidence_qualified = mandatory_executed = mandatory_required = human_required = 0
            for record in trace:
                claim = reread.get(ClaimEntry, record["claim_id"])
                snapshot = reread.get(AuditSnapshot, record["snapshot_id"])
                case = reread.get(GovernanceCase, record["case_id"])
                hold = reread.get(GovernanceEvent, record["hold_event_id"])
                event = reread.scalar(select(AuditLog).where(AuditLog.action == "claim_inputs_audited",
                    AuditLog.resource_id == claim.id))
                batch = reread.get(ClaimBatch, claim.batch_id)
                source_record = reread.get(ExtractedSourceRecord, claim.extracted_record_id)
                findings = snapshot.findings
                certificates = findings["reference_certificates"]
                if (claim.organization_id != org_id or snapshot.organization_id != org_id
                    or case.organization_id != org_id or batch.ingestion_document_id != document_id
                    or any(claim.source_locator.get(key) != value for key, value in source_record.locator.items())
                    or claim.source_values != source_record.values
                    or claim.source_locator["index"] != 1 or claim.source_locator["row"] < 2
                    or event.details["audit_snapshot_id"] != snapshot.id or event.actor_id != actor_id
                    or event.details["source_sha256"] != sources[0]["sha256"]
                    or case.audit_snapshot_id != snapshot.id or hold.case_id != case.id or hold.kind != "hold"
                    or len(certificates) != 6 or {item["family"] for item in certificates} != set(FAMILIES)
                    or snapshot.calculation["status"] != "held" or snapshot.calculation["payable"] is not None
                    or findings["financial_decision"] != "not_authorized"):
                    raise AssertionError("postcommit lineage/advisory mismatch")
                if any(token in json.dumps(event.details) for token in (claim.claim_reference, claim.beneficiary_token, claim.provider_code)):
                    raise AssertionError("sensitive token in shared event")
                completed_refs += sum(item.get("approved") is True and item.get("complete") is True
                    and item.get("lookup_status") == "reference_applicable" and not item.get("gaps")
                    and bool(item.get("source_evidence")) for item in certificates)
                outcomes[findings["audit_state"]] += 1
                evidence_qualified += bool(findings["source_evidence"]) and any(
                    item["agent"] == "evidence" and item["audit_state"] == "MATCH_VERIFIED" for item in findings["agents"])
                mandatory_required += findings["coverage"]["required"]
                mandatory_executed += findings["coverage"]["executed"]
                human_required += findings["human_review_required"] is True
                record.update({"organization_id": org_id, "source_document_id": document_id,
                    "source_sha256": sources[0]["sha256"], "source_record_id": claim.extracted_record_id,
                    "source_locator": claim.source_locator, "audit_event_id": event.id,
                    "actual_state": findings["audit_state"], "reason_code": findings["reason_code"],
                    "references": event.details["references"], "rule_results": findings["agents"]})
            if outcomes != {"MATCH_VERIFIED": size} or completed_refs != size * 6 or evidence_qualified != size:
                raise AssertionError("fully sourced matching sample failed expected state/coverage")
            result.update({"durable_counts": durable_counts, "outcomes": dict(outcomes),
                "reference_coverage": ratios(completed_refs, size * 6),
                "qualified_evidence_coverage": ratios(evidence_qualified, size),
                "mandatory_check_coverage": ratios(mandatory_executed, mandatory_required),
                "human_review_flag": ratios(human_required, size), "human_hold_routing": ratios(size, size),
                "unresolved_fraction": ratios(outcomes["UNRESOLVED"], size),
                "unavailable_fraction": ratios(outcomes["AUDIT_UNAVAILABLE"], size),
                "quarantined_records": reread.scalar(select(func.count()).select_from(QuarantineItem))})
        result.update({"measurement_status": "INTEGRATION VERIFIED", "sources": sources, "trace": trace,
            "workload": {"files": 8, "excel_files": 1, "excel_sheets": 2,
                "excel_data_rows": size + 1, "excel_rows_including_headers": size + 3,
                "claims": size, "independent_beneficiaries": size, "payment_rows_excluded": 1,
                "all_source_data_records": sum(item["records"] for item in sources),
                "reference_data_records": 3 * size + 3, "execution_data_records": size,
                "source_bytes": sum(item["bytes"] for item in sources)},
            "errors": 0, "stalls": 0, "automatic_retries": 0})
    except Exception as exc:
        # Never include exception text, a connection URL, source values or credentials.
        result["failure"] = {"stage": measurements.failure_stage or measurements.stage,
                             "exception_type": type(exc).__name__}
        result["errors"] = 1
        result["stalls"] = int(isinstance(exc, TimeoutError))
    finally:
        signal.alarm(0)
        with measurements.measure("schema_cleanup"):
            try:
                if created:
                    with engine.begin() as connection:
                        connection.execute(text("SET LOCAL statement_timeout = 5000"))
                        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
                result["schema_removed"] = created
            except Exception as exc:
                result["measurement_status"] = "FAILED"
                result["cleanup_failure"] = type(exc).__name__
                result["schema_removed"] = False
        engine.dispose()
        result["sample_wall_seconds_including_setup_validation_cleanup"] = time.perf_counter() - start
        result["client_cpu_seconds"] = time.process_time() - cpu_start
        child_end = resource.getrusage(resource.RUSAGE_CHILDREN)
        result["parser_children_cpu_seconds"] = (child_end.ru_utime + child_end.ru_stime
            - child_start.ru_utime - child_start.ru_stime)
        result["client_peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        result["max_single_child_peak_rss_bytes"] = child_end.ru_maxrss * 1024
        result["timings_seconds"] = dict(measurements.seconds)
        result["measured_calls"] = dict(measurements.calls)
        result["measured_work_counts_initial_audits_only"] = dict(measurements.work_counts)
        if measurements.calls["g5_audit_and_shared_event"]:
            result["g5_timing_partition"] = timing_partition(measurements.seconds["g5_audit_and_shared_event"],
                measurements.seconds["inspection_inclusive"], measurements.seconds["reference_lookup_inclusive"])
        if result.get("pipeline_wall_seconds"):
            result["claims_per_pipeline_second"] = size / result["pipeline_wall_seconds"]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="10,25,100")
    parser.add_argument("--max-seconds", type=int, default=300)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker-size", type=int, choices=SIZES, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        sizes = [args.worker_size] if args.worker_size else [int(value) for value in args.sizes.split(",")]
        url = os.getenv("MCIAS_BENCHMARK_DATABASE_URL", "")
        validate_target(url, os.getenv("MCIAS_BENCHMARK_ALLOW"), sizes, args.max_seconds)
        if os.getenv("MCIAS_ENVIRONMENT") != "development" or os.getenv("MCIAS_MALWARE_SCAN") != "disabled":
            raise ValueError("explicit development and synthetic malware-scan mode required")
        if args.output is None:
            raise ValueError("--output required")
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.worker_size:
        measurements = Measurements()
        def deadline(_signum, _frame):
            raise TimeoutError("bounded synthetic sample deadline")
        signal.signal(signal.SIGALRM, deadline)
        signal.alarm(args.max_seconds)
        with tempfile.TemporaryDirectory(prefix="mcias-native-sample-") as directory:
            result = _run_sample(args.worker_size, url, measurements, Path(directory), args.max_seconds)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0 if result["measurement_status"] == "INTEGRATION VERIFIED" else 1
    report = {"kind": "bounded_native_synthetic_inputs_first_benchmark", "report_schema": 1,
        "started_at_utc": datetime.now(timezone.utc).isoformat(), "requested_sizes": sizes,
        "method": {"database": "local PostgreSQL16, disposable schema per size, ORM metadata creation; not migration verification",
            "process": "fresh Linux Python process per size; sequential concurrency=1",
            "cpu": "process_time client process; RUSAGE_CHILDREN parser child user+system CPU separately; excludes PG server",
            "memory": "Linux getrusage ru_maxrss*1024: fresh client lifetime high water; maximum single parser child separately; not sum; excludes PG server",
            "timing": "perf_counter wall seconds; G3 inclusive reference lookup nested in inspection nested in G5; partition subtracts overlap",
            "setup_overlap": "g3_reference_source_setup and execution_source_and_attachment_setup include their G2 ingestion/readback; never sum all timing fields",
            "retry": "one same-byte workbook reimport plus first/last G5 snapshot and G6 open_case replay; no duplicate hold request",
            "scope": "fully sourced matching synthetic claims only; not quality precision/recall, concurrency, SLA, OCR or production readiness"},
        "samples": []}
    with tempfile.TemporaryDirectory(prefix="mcias-native-report-") as directory:
        for size in sizes:
            output = Path(directory) / f"sample-{size}.json"
            try:
                completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker-size", str(size),
                    "--max-seconds", str(args.max_seconds), "--output", str(output)],
                    timeout=args.max_seconds + 15, capture_output=True, text=True)
                sample = json.loads(output.read_text()) if output.exists() else {
                    "size": size, "measurement_status": "FAILED", "failure": {"stage": "worker", "exception_type": "MissingWorkerReport"}}
                sample["worker_exit_code"] = completed.returncode
            except subprocess.TimeoutExpired:
                sample = {"size": size, "measurement_status": "FAILED", "failure": {"stage": "worker", "exception_type": "ProcessTimeout"}}
            report["samples"].append(sample)
            report["stopped_after_failure"] = sample["measurement_status"] != "INTEGRATION VERIFIED"
            args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps({"size": size, "measurement_status": sample["measurement_status"],
                "pipeline_wall_seconds": sample.get("pipeline_wall_seconds"), "failure": sample.get("failure")}), flush=True)
            if report["stopped_after_failure"]:
                break
    return 1 if report["stopped_after_failure"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
