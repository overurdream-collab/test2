"""Run locally via institution-owned scheduler; never transfers data externally."""
import argparse, json, os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from mcias.config import Settings
from mcias.models import AuditLog
from mcias.retention import run_archive
from mcias.rate_limits import cleanup

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id")
    parser.add_argument("--cleanup-rate-buckets", action="store_true")
    args = parser.parse_args()
    engine = create_engine(Settings().database_url)
    try:
        with Session(engine) as db:
            if args.cleanup_rate_buckets:
                print(json.dumps({"buckets_removed": cleanup(db)})); return
            key = bytes.fromhex(os.environ["MCIAS_RETENTION_ENCRYPTION_KEY"])
            if len(key) != 32: raise ValueError("32-byte archive key required")
            directory = os.environ["MCIAS_RETENTION_ARCHIVE_DIR"]
            completed = select(AuditLog.resource_id).where(AuditLog.action == "retention_archive_verified")
            ids = [args.job_id] if args.job_id else list(db.scalars(select(AuditLog.resource_id).where(
                AuditLog.action == "retention_archive_requested", AuditLog.resource_id.not_in(completed)).limit(100)))
            for job_id in ids:
                print(json.dumps({"job_id": job_id, **run_archive(db, job_id, directory, key)}))
    finally:
        engine.dispose()

if __name__ == "__main__": main()
