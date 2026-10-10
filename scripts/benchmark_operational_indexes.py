"""Read-only EXPLAIN comparisons with temporary transaction-local indexes.

Run on a dedicated 10K synthetic *_e2e database, never production. Index DDL is
rolled back. JSON contains plans/timing, not medical rows or connection strings.
"""
import json, os
from pathlib import Path
from sqlalchemy import create_engine, text
from mcias.seed.config import SeedConfig
from mcias.seed.loader import identifier

QUERIES = {
    "claim_org_date": ("claim_entries", ["organization_id", "service_date"],
        "SELECT id FROM claim_entries WHERE organization_id=:org AND service_date BETWEEN '2026-09-01' AND '2026-09-07'"),
    "claim_org_provider": ("claim_entries", ["organization_id", "provider_code"],
        "SELECT id FROM claim_entries WHERE organization_id=:org AND provider_code='SYN-PROVIDER-42'"),
    "claim_org_beneficiary": ("claim_entries", ["organization_id", "beneficiary_token"],
        "SELECT id FROM claim_entries WHERE organization_id=:org AND beneficiary_token='SYN-BEN-42'"),
    "audit_org_created": ("audit_snapshots", ["organization_id", "created_at"],
        "SELECT id FROM audit_snapshots WHERE organization_id=:org ORDER BY created_at DESC LIMIT 50"),
    "report_org_batch": ("report_snapshots", ["organization_id", "batch_id"],
        "SELECT id FROM report_snapshots WHERE organization_id=:org AND batch_id=:batch"),
}

def main():
    config = SeedConfig(os.environ["MCIAS_E2E_DATABASE_URL"], os.environ.get("MCIAS_ENVIRONMENT", ""), count=10000)
    config.validate()
    engine = create_engine(config.database_url)
    result = {"claim_count": 0, "queries": {}, "governance_case_version": "existing UNIQUE index; not duplicated"}
    try:
        with engine.connect() as db:
            result["claim_count"] = db.scalar(text("SELECT count(*) FROM claim_entries"))
            if result["claim_count"] < 10000: raise ValueError("10K synthetic claims required")
            db.execute(text("ANALYZE claim_entries"))
            params = {"org": identifier("organization"), "batch": identifier("batch")}
            for name, (table, columns, sql) in QUERIES.items():
                before = db.scalar(text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql), params)
                db.execute(text("CREATE INDEX bench_" + name + " ON " + table + " (" + ",".join(columns) + ")"))
                after = db.scalar(text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql), params)
                result["queries"][name] = {"before": before, "after": after,
                    "table_rows": db.scalar(text("SELECT count(*) FROM " + table))}
            db.rollback()
        path = Path(os.environ.get("MCIAS_BENCHMARK_OUTPUT", ".e2e-output/index-benchmark.json"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + "\n")
        print("Benchmark evidence written; temporary indexes rolled back.")
    finally:
        engine.dispose()

if __name__ == "__main__": main()
