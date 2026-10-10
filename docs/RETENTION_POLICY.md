# Audit retention and local archival

Seven years is a proposed institutional retention period, not an approved policy.
Deletion/purge is disabled. Existing append-only database triggers remain intact.
No migration partitions or rewrites existing immutable audit tables.

## Operational interface

- `GET /api/v1/admin/retention/status`: authenticated `retention.read`.
- `POST /api/v1/admin/retention/archive`: authenticated `retention.archive`; JSON `{"month":"2020-01"}`; returns 202 and a job UUID.
- `/admin/backups` displays status and requests archival. Archive is not a backup/restore service for the entire database.
- Institution scope comes from the authenticated user, never from request input.
- Only audit rows whose actor belongs to that institution are included. System/null-actor logs are excluded; they require a separately governed administrator archive mechanism.

Run the worker locally under a restricted service account, with secrets outside the repository:

```sh
python scripts/retention_worker.py
python scripts/retention_worker.py --job-id JOB_UUID
python scripts/retention_worker.py --cleanup-rate-buckets
```

Required environment: `MCIAS_DATABASE_URL`, `MCIAS_RETENTION_ARCHIVE_DIR` (institution-owned local directory), `MCIAS_RETENTION_ENCRYPTION_KEY` (64 hex characters, independently managed 32-byte key). The worker rechecks actor activity, institution and permission. Schedule it using the institution's scheduler; installation does not silently enable a privileged task.

Archives are monthly encrypted files using the existing AES-GCM authenticated backup format. Private temporary files are fsynced, decrypted and compared before atomic publication. SHA-256/row-count receipts are appended to audit_log. Retrying a completed job returns its receipt. Originals remain unchanged. Files are mode 0600; directory creation uses 0700. Operators must protect parent directories and maintain key escrow/rotation and access controls.

The worker is bounded to 10,000 rows per monthly job and the existing 128 MiB bundle safety cap. Larger deployments need a streaming worker before operational rollout. No external S3 transfer is implemented. An institution-owned compatible store can be added after access/custody approval.

## Acceptance blockers

Institutional policy must define retention start date, legal holds, exceptions, authorized destruction and independent approval. A restore drill and custody verification are required before any future purge. Readback integrity verification is implemented; a full institutional restore acceptance is not implied. Database partition conversion and deletion are intentionally deferred because existing audit immutability prevents deletion.
