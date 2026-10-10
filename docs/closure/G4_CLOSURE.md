# G4 — Claims | Closure record (2026-10-10)

**Status: OPEN — engineering regression passed; institutional acceptance not yet signed.**

## Deliverables
- Tenant-scoped claim batches, source-linked immutable claim entries and evidence attachments.
- Strict Decimal/date normalization, row-level rejection and review holds, bounded resumable import with idempotent checkpoints.
- PostgreSQL source-provenance triggers and claims API; originals and locators retained.

## Tests and evidence
- T09 synthetic mixed-validity rows and T16 interrupted-transaction rollback/retry, bounded resume and duplicate prevention.
- Synthetic 1,001-record import, cross-tenant attachment denial and PostgreSQL trigger-installation check.
- Latest CI: https://github.com/overurdream-collab/test2/actions/runs/38010322075
- Tested commit `626640c1496c3bc4c71fa8fd64dfb315d4fd7035`: 112 unit passed / 10 skipped; 65 PostgreSQL integration passed; dependency audit successful.
- These are synthetic tests; a real process kill and restart, full-scale SLA load, and live storage-integrity drill are **not** evidenced.

## Deferred
- Institution-sized throughput and concurrency benchmark against approved target volumes.
- Full missing-evidence hold policy and end-to-end operational recovery/attachment-storage validation.

## Waiting on
- Target claim volumes and SLA, production-like interrupted-worker and restore drill, institutional sample-data acceptance.
- Signed G1–G3 prerequisites and authorized human G4 gate signoff.
