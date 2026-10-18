# DG-001 — Shared Audit Writer foundation (scope: G3 contract revision only)

Baseline: `26fd244e8ea4905cf9aa4b0bba19bda90c45ac33`. Existing `audit_log` was reused, including SQLAlchemy append-only guards, existing PostgreSQL immutable trigger, tenant-scoped metadata-only reader `GET /api/v1/workspace/activity`, and existing RBAC. **No second AuditLog table, reader, or permission subsystem.**

## Shared integration contract
`mcias.audit_writer.write_event(db, *, actor, organization_id, action, resource_type, resource_id, outcome, details)` stages an audit event in the caller transaction. The caller commits/rolls back that transaction. The writer rejects mismatched active actor/organization and non-enumerated outcomes. A fixed allowlist strips every other detail including medical fields, session tokens, passwords and free-text notes. Allowed changes are only bounded metadata: version, previous_version, previous_id, new_id, effective_from, effective_until, reason_code, contract_number, status.

`mcias.audit_writer.record_outcome_independent(bind, *, actor_id, organization_id, action, resource_type, resource_id, outcome, details)` creates a separate transaction **after the business transaction rolls back** and verifies actor organization before commit. It is for rejected/failed attempts only; its failure raises, never silently hides missing audit events. Avoid using a concurrent independent transaction while another business transaction holds locks on the same actor row.

## First integration
Existing G3 `revise_contract_draft` stages `contract_draft_revised / success` before the existing commit. Existing revision FastAPI endpoint writes `contract_revision_denied / denied` on `HTTPException` returned by current `_perform`, after `db.rollback()`. No G3 contract approval/tariff policy changes. Other G3 authorization failures are already guarded by the existing `tenant_access_denied` event and its own commit, not yet migrated to this new writer.

## Acceptance and limits
Existing strict Chromium → FastAPI → PostgreSQL 16 harness now asserts: modified contract success event and tenant reference; an attempted stale revision HTTP409; denial event survives rollback and does not include contract notes; privileged SQL UPDATE and DELETE against `audit_log` fail and original row remains; existing activity reader sees permitted events but hides raw JSON and cross-tenant traps. Existing reader attempts HTTP403 already exercised. Dedicated artifact contains `results.json` and browser screenshots.

This is a **foundation**, NOT a declaration that all MCIAS actions are recorded. The event table's legacy structure lacks explicit indexed tenant/result/request/trace columns, and existing actor-linked reader cannot show null/system actor events. Durable error logging for arbitrary server crashes and cross-process failures, separation of database-owner vs constrained runtime role, hash chaining, full-field provenance and event signing remain subsequent hardening gates. PostgreSQL OWNER/SUPERUSER can bypass normal table privileges; neither this API nor the current DB trigger proves protection against that class of administrator. Future A1/Contract Intelligence integration must follow the same writer interface and separate transaction contract after independent security review.

No main merge or production deployment. No real user medical records.
