# G1 on-premises security baseline (deployment checklist)

The following controls are mandatory and must be verified in the target environment before gate acceptance. This document does not claim they have been deployed.

## Network and TLS
- Serve application behind an on-premises TLS 1.2+ reverse proxy with a trusted organization-issued certificate; redirect HTTP to HTTPS.
- Do not expose PostgreSQL, Redis or encrypted source storage to public networks.
- Enforce security headers at proxy: Strict-Transport-Security (HTTPS only), X-Content-Type-Options: nosniff, Referrer-Policy: no-referrer and a reviewed Content-Security-Policy.
- Deny production /docs and /openapi.json unless an authenticated administrative network policy permits them.
- Use a private, monitored DNS name; log TLS certificate expiry.

## PostgreSQL least privilege
- Database migration account is separate from application account and is disabled for routine application requests.
- Application role must not own tables, schemas, triggers or functions, must not have CREATE on public schema, and must not be superuser, CREATEDB, CREATEROLE, BYPASSRLS or REPLICATION.
- REVOKE ALL ON SCHEMA public FROM PUBLIC; explicitly GRANT USAGE on application schema to runtime role.
- Grant only required SELECT/INSERT/UPDATE on individual tables; audit_log runtime role may INSERT and SELECT but never UPDATE or DELETE.
- Block DELETE/UPDATE of protected records at both role and trigger layers. Verify using runtime credentials (not migration credentials).
- Protect backups and secrets with separate OS identities, offline copies, and restricted filesystem ACLs.
- Consider separate DB ownership and tamper-evident off-database audit sink: DB superusers can disable triggers.

## Operations evidence
- Record server OS, PostgreSQL version, certificate chain validation, TLS scan, DB role privilege query, immutable audit negative test, backup/restore command and reviewer.
- Record SHA-256 digests for source artifacts and prove recovery with original encryption key.
- Incident procedure: revoke sessions, rotate compromised keys, restore from verified offline backup, preserve append-only evidence.

## Pending human and infrastructure actions
- Approved G0 threat model and ADRs.
- Organization-head authorization and signature validation procedure.
- MFA bootstrap and recovery identity checks with independent approvers.
- Production key custody and full rotation with tested rollback.
- Target-environment TLS, DB least-privilege, backup and penetration-test evidence.
