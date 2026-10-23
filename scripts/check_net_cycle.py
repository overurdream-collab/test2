#!/usr/bin/env python3
"""Observe a real synthetic NET audit cycle, then scale only after it passes.

Requires the repository's test dependencies. Never connects to a configured
database: every size runs in a separate process with a fresh in-memory SQLite
database and temporary encrypted source storage. No migrations are executed.
This is a measurement utility, not a production capacity or SLA assertion.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from time import perf_counter
import traceback
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BUCKETS = ("accepted", "rejected", "held", "review")
MEASURED_SOURCE_FILES = (
    "scripts/check_net_cycle.py", "mcias/audit_engine.py", "mcias/audit_service.py", "mcias/palermo2.py",
    "mcias/services/net_audit_service.py", "mcias/services/invoice_service.py", "mcias/services/result_service.py",
    "mcias/services/claim_reference_service.py", "mcias/claim_batches.py",
    "tests/workspace_v2/net_cycle_fixtures.py", "tests/workspace_v2/invoice_fixtures.py",
)


def source_hashes():
    return {str(path): sha256((ROOT / path).read_bytes()).hexdigest() for path in MEASURED_SOURCE_FILES}


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def timed(stages, name, operation):
    started = perf_counter()
    result = operation()
    stages[name] = round(perf_counter() - started, 6)
    return result


def worker(size, artifact_directory=None):
    """Use real HTTP and signed synthetic institutional policy enrollment."""
    sys.path.insert(0, str(ROOT))
    stages = {}
    started = perf_counter()
    with tempfile.TemporaryDirectory(prefix="mcias-net-cycle-") as directory:
        location = Path(directory)
        # Set these before importing the application; never inherit a live DB.
        os.environ.update({
            "MCIAS_ENVIRONMENT": "development",
            "MCIAS_DATABASE_URL": "sqlite://",
            "MCIAS_TEST_DATABASE_URL": "sqlite://",
            "MCIAS_LAPTOP_TEST_MODE": "synthetic_localhost",
            "MCIAS_RBAC_AUTHORITY": "super_admin",
            "MCIAS_STORAGE_DIR": str(location / "sources"),
            "MCIAS_STORAGE_KEY": os.urandom(32).hex(),
            "MCIAS_RBAC_TRUST_REGISTRY": str(location / "trust.json"),
        })
        trust = location / "trust.json"
        trust.write_text('{"trusted_approvers":{}}', encoding="utf-8")
        trust.chmod(0o600)
        import pytest
        from openpyxl import load_workbook
        from pypdf import PdfReader
        from sqlalchemy import select, func
        from sqlalchemy.orm import Session
        from mcias.app import app, get_rate_limit_db
        from mcias.models import SourceFile
        from mcias.models_audit import AuditSnapshot
        from mcias.models_claims import ClaimEntry, ClaimAttachment
        from mcias.models_ingestion import IngestionDocument
        from mcias.services.registry_service import store
        from tests.api.conftest import api_factory, synthetic_password_hash
        from tests.features.conftest import features_api
        from tests.workspace_v2.test_access_and_registry import workspace
        from tests.workspace_v2.test_linked_references import linked
        from tests.workspace_v2.invoice_fixtures import attach_invoices
        from tests.workspace_v2.net_cycle_fixtures import (
            case_row, import_cases, configure_signers,
            approve_batch_policies, execute_batch, result_files,
        )

        monkeypatch = pytest.MonkeyPatch()
        factory = None
        try:
            preparation_started = perf_counter()
            factory = api_factory.__wrapped__(monkeypatch, synthetic_password_hash.__wrapped__())
            make = next(factory)
            api = features_api.__wrapped__(make)
            api = workspace.__wrapped__(api, monkeypatch, location)
            api = linked.__wrapped__(api, monkeypatch)
            # Rate limiting uses the same explicitly isolated database.
            app.dependency_overrides[get_rate_limit_db] = api.database
            configure_signers(api, monkeypatch)
            stages["isolated_setup"] = round(perf_counter() - preparation_started, 6)

            cases, expected_by_reference = [], {}
            for index in range(1, size + 1):
                kind = BUCKETS[(index - 1) % 4]
                overrides = {"gross": "1200", "unit": "1200", "copay": "120", "net": "1080"} if kind == "rejected" else {}
                if kind == "review":
                    overrides["name"] = "SYN wrong identity"
                row = case_row(index, **overrides)
                cases.append(row)
                expected_by_reference[row["invoice_reference"]] = kind
            missing = {key for key, value in expected_by_reference.items() if value == "held"}
            batch = timed(stages, "xlsx_ingestion_mapping_import", lambda: import_cases(api, cases, attach=False))
            missing_ids = {batch.identities[key] for key in missing}
            invoice_id, invoice_raw = timed(stages, "pdf_ingestion_and_per_line_links",
                lambda: attach_invoices(api, batch.batch_id, skip_ids=missing_ids))
            invoice_pages = len(PdfReader(BytesIO(invoice_raw), strict=True).pages)
            check(invoice_pages == size, "Synthetic invoice bundle does not contain one page per service")

            def recheck():
                response = api.client.post(f"/api/v1/claims/batches/{batch.batch_id}/reference-checks", headers=api.headers["root"])
                check(response.status_code == 201, response.text)
                return response.json()

            timed(stages, "reference_recheck", recheck)
            policies = timed(stages, "signed_policy_enrollment", lambda: approve_batch_policies(api, batch.batch_id))
            run = timed(stages, "net_audit_and_palermo2", lambda: execute_batch(api, batch.batch_id))
            expected = {batch.identities[key]: value for key, value in expected_by_reference.items()}
            actual = {row["line_id"]: row["bucket"] for row in run["rows"]}
            expected_counts = {key: sum(value == key for value in expected.values()) for key in BUCKETS}
            check(len(actual) == size and set(actual) == set(expected), "Audit omitted or duplicated an input service line")
            check(run["counts"] == expected_counts, f"Incorrect bucket counts: {run['counts']} expected {expected_counts}")
            check(actual == expected, "A service line differs from the predefined oracle")
            check(all(row["reason"] == "missing_invoice" for row in run["rows"] if row["line_id"] in missing_ids), "Missing invoice reason was not preserved")

            # The one-line gate includes the existing real human approval flow.
            def human_approval():
                snapshot = run["rows"][0]["snapshot_id"]
                response = api.client.post("/api/v1/governance/cases/from-audit/" + snapshot, headers=api.headers["root"])
                check(response.status_code == 201, response.text)
                path = "/api/v1/governance/cases/" + response.json()["id"] + "/events"
                response = api.client.post(path, json={"kind": "propose", "payload": {"reason_code": "SYN_REVIEWED"}}, headers=api.headers["root"])
                check(response.status_code == 201, response.text)
                check(api.client.post(path, json={"kind": "approve", "payload": {}}, headers=api.headers["root"]).status_code == 403,
                    "Technical super-admin gained implicit financial approval")
                response = api.client.post(path, json={"kind": "approve", "payload": {"reason_code": "SYN_APPROVED"}}, headers=api.headers["none"])
                check(response.status_code == 201, response.text)
                return True

            approved = timed(stages, "human_approval_gate", human_approval) if size == 1 else False
            result, archive_raw = timed(stages, "freeze_and_download_four_files", lambda: result_files(api, batch.batch_id))
            check(result["summary"]["counts"] == expected_counts, "Frozen files differ from the real audit manifest")
            check(result["financially_final"] is False, "Preliminary result export incorrectly claims financial finality")
            exported = {}
            with ZipFile(BytesIO(archive_raw)) as archive:
                check(set(archive.namelist()) == {key + ".xlsx" for key in BUCKETS}, "Output ZIP is not exactly four disjoint files")
                for key in BUCKETS:
                    book = load_workbook(BytesIO(archive.read(key + ".xlsx")), read_only=True)
                    rows = list(book.active.values)[1:]
                    for row in rows:
                        check(row[0] not in exported, "A service line appears in more than one output")
                        exported[row[0]] = key
                        if row[0] in missing_ids:
                            check("نقص المرفقات" in str(row[9]), "Held output does not explain missing invoice")
                    book.close()
            check(exported == expected, "Output file membership differs from the oracle")

            financial_count, claimed_sum, payable_sum, deduction_sum = 0, Decimal(0), Decimal(0), Decimal(0)
            with Session(api.engine) as db:
                check(db.scalar(select(func.count()).select_from(ClaimEntry).where(ClaimEntry.batch_id == batch.batch_id)) == size, "Wrong imported line count")
                workbook_source = db.get(SourceFile, db.get(IngestionDocument, batch.document_id).source_id)
                invoice_source = db.get(SourceFile, db.get(IngestionDocument, invoice_id).source_id)
                check(workbook_source.sha256 == sha256(batch.raw).hexdigest(), "Original XLSX hash changed")
                check(store().get(workbook_source.storage_key, workbook_source.sha256) == batch.raw, "Original XLSX bytes changed")
                check(invoice_source.sha256 == sha256(invoice_raw).hexdigest(), "Invoice PDF hash changed")
                check(store().get(invoice_source.storage_key, invoice_source.sha256) == invoice_raw, "Invoice PDF bytes changed")
                links = db.scalar(select(func.count()).select_from(ClaimAttachment).where(ClaimAttachment.claim_id.in_(expected)))
                documents = db.scalar(select(func.count(func.distinct(ClaimAttachment.ingestion_document_id))).where(ClaimAttachment.claim_id.in_(expected)))
                check(links == size - len(missing_ids), "Invoice link count differs from individual service coverage")
                snapshot_ids = [row["snapshot_id"] for row in run["rows"] if row["snapshot_id"]]
                snapshots = list(db.scalars(select(AuditSnapshot).where(AuditSnapshot.id.in_(snapshot_ids))))
                check(len(snapshots) == size - len(missing_ids), "Unexpected number of actual immutable audit snapshots")
                for snapshot in snapshots:
                    calc = snapshot.calculation
                    if actual[snapshot.claim_id] == "review":
                        check(calc["status"] == "held" and snapshot.verification["status"] == "held",
                            "Unresolved identity review incorrectly produced a verified financial calculation")
                        continue
                    check(snapshot.verification["status"] == "verified", "Palermo-2 did not verify an actual snapshot")
                    claimed, payable, deduction = (Decimal(str(calc[key])) for key in ("claimed", "payable", "total_deduction"))
                    check(claimed == payable + deduction, "NET financial conservation failed")
                    check(calc["copay_deducted_again"] is False, "Beneficiary copay was deducted again")
                    if actual[snapshot.claim_id] == "accepted":
                        check((claimed, payable, deduction) == (Decimal(900), Decimal(900), Decimal(0)), "Incorrect accepted NET amount")
                    if actual[snapshot.claim_id] == "rejected":
                        check((claimed, payable, deduction) == (Decimal(1080), Decimal(900), Decimal(180)), "Incorrect rejected NET amount")
                    financial_count += 1
                    claimed_sum += claimed; payable_sum += payable; deduction_sum += deduction
                check(financial_count == expected_counts["accepted"] + expected_counts["rejected"],
                    "A finalizable financial snapshot is missing or a review was counted as approved")

            elapsed = perf_counter() - started
            pipeline_seconds = sum(value for key, value in stages.items() if key not in ("isolated_setup", "human_approval_gate"))
            confusion = {truth: {observed: sum(expected[line] == truth and actual[line] == observed for line in expected)
                for observed in BUCKETS} for truth in BUCKETS}
            class_metrics = {}
            for key in BUCKETS:
                true_positive = confusion[key][key]
                predicted = sum(confusion[truth][key] for truth in BUCKETS)
                support = sum(confusion[key].values())
                class_metrics[key] = {"support": support,
                    "precision": true_positive / predicted if predicted else None,
                    "recall": true_positive / support if support else None}
            if artifact_directory:
                target = Path(artifact_directory) / f"{size}-lines"
                target.mkdir(parents=True, exist_ok=True)
                (target / "synthetic-claims-original.xlsx").write_bytes(batch.raw)
                (target / "synthetic-invoices.pdf").write_bytes(invoice_raw)
                (target / "four-exclusive-results.zip").write_bytes(archive_raw)
            try:
                import resource
                max_rss_mib = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 if sys.platform != "darwin" else 1024 * 1024), 3)
            except ImportError:
                max_rss_mib = None
            return {
                "status": "passed", "service_lines": size,
                "expected_counts": expected_counts, "observed_counts": run["counts"],
                "exact_accuracy": 1.0, "confusion_matrix": confusion, "class_metrics": class_metrics,
                "unique_exported_lines": len(exported), "exclusive_complete_outputs": True,
                "original_xlsx_sha256": sha256(batch.raw).hexdigest(), "original_bytes_preserved": True,
                "invoice_pdf_sha256": sha256(invoice_raw).hexdigest(), "invoice_bytes_preserved": True,
                "invoice_pdf_documents_uploaded": 1, "invoice_pdf_pages": invoice_pages,
                "invoice_documents_linked": documents, "per_service_invoice_links": links,
                "unlinked_service_lines": len(missing_ids), "missing_invoice_held_correctly": True,
                "signed_policy_fingerprints": len({item["fingerprint"] for item in policies.values()}),
                "real_audit_snapshots": len(snapshots), "real_verified_financial_snapshots": financial_count,
                "snapshot_financial_conservation": {"scope": "verified accepted/rejected snapshots only; held/review never counted as financial approval",
                    "claimed": str(claimed_sum), "payable": str(payable_sum), "deductions": str(deduction_sum)},
                "human_approval_gate_proven": approved, "preliminary_exports_financially_final": False,
                "stage_seconds": stages, "worker_elapsed_seconds": round(elapsed, 6),
                "pipeline_seconds": round(pipeline_seconds, 6),
                "pipeline_lines_per_second": round(size / pipeline_seconds, 6),
                "audit_lines_per_second": round(size / stages["net_audit_and_palermo2"], 6),
                "process_peak_rss_mib": max_rss_mib,
            }
        finally:
            if factory is not None:
                factory.close()
            monkeypatch.undo()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="1,10,50,100", help="Increasing service-line counts, starting at 1 (maximum 1000)")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evidence/net-cycle/performance.json")
    parser.add_argument("--artifacts-dir", type=Path, help="Optional directory for synthetic originals, PDF and four-file ZIP per size")
    parser.add_argument("--worker-lines", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_lines is not None:
        if not 1 <= args.worker_lines <= 1000:
            parser.error("Worker count must remain within the existing 1000-line limit")
        try:
            with redirect_stdout(sys.stderr):
                result = worker(args.worker_lines, args.artifacts_dir)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        except Exception as error:
            traceback.print_exc(file=sys.stderr)
            print(json.dumps({"status": "failed", "service_lines": args.worker_lines, "error_type": type(error).__name__, "error": str(error)}, ensure_ascii=False))
            return 1
    try:
        sizes = [int(value) for value in args.sizes.split(",")]
    except ValueError:
        parser.error("--sizes must be comma-separated integers")
    if not sizes or sizes[0] != 1 or sizes != sorted(set(sizes)) or sizes[-1] > 1000:
        parser.error("--sizes must start at 1, increase strictly, and remain within the existing 1000-line limit")
    report = {
        "schema_version": 1,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_working_tree": subprocess.check_output(["git", "status", "--short", "--untracked-files=no"], cwd=ROOT, text=True).splitlines(),
        "code_sha256": source_hashes(),
        "platform": platform.platform(), "python": platform.python_version(),
        "database": "isolated in-memory SQLite per fresh subprocess; no migrations",
        "transport": "FastAPI TestClient; in-process actual HTTP routes",
        "synthetic": True, "production_acceptance": False, "runtime_sla_asserted": False,
        "workload": "One accepted line first; then repeating accepted, proven NET price difference, missing invoice, identity review cases",
        "limitations": ["Synthetic data and SQLite do not prove laptop, PostgreSQL, concurrent production load or institutional acceptance.",
            "One multi-page PDF bundle is explicitly linked per covered service; PDF content is operator-classified, not OCR-verified.",
            "Audit/exports remain preliminary; only the one-line gate exercises an explicitly authorized human approval.",
            "Peak RSS is a separate worker process high-water including interpreter, imports, setup and complete cycle.",
            "Financial volume is not used to infer claim counts, required throughput or an SLA."],
        "runs": [],
    }
    exit_code = 0
    for size in sizes:
        command = [sys.executable, str(Path(__file__).resolve()), "--worker-lines", str(size)]
        if args.artifacts_dir:
            command += ["--artifacts-dir", str(args.artifacts_dir.resolve())]
        print(f"Measuring {size} service lines...", flush=True)
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError:
            result = {"status": "failed", "service_lines": size, "error": "Worker did not return JSON", "worker_stderr": completed.stderr[-5000:]}
        if source_hashes() != report["code_sha256"]:
            result.update(status="invalidated", error="Measured source changed during this benchmark; rerun on a stable tree")
        report["runs"].append(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if completed.returncode != 0 or result.get("status") != "passed":
            print(completed.stderr[-5000:], file=sys.stderr)
            exit_code = 1
            break  # Never scale beyond a failed smaller cycle.
    print(f"Observed evidence: {args.output}", flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
