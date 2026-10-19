# DG-001 — Shared Audit Writer — Phase 1 worklog / HANDOFF

Date: 2026-10-19. Status: DRAFT / PHASE 1 ONLY / NOT OPERATIONALLY ACCEPTED.
Branch: feat/mcias-shared-audit-writer-phase1.
Baseline main: b69defa2f621458ef44d790b510840307a81009a.
Source PR25: a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1.
Reference PR28: 65bbddc1ae95aed22e157774f600a296a6e43926.
Source mcias/audit_writer.py Git blob SHA: 509ce4124f012cc4a121294fe9122c9384902fd6.
Original file transferred byte-equivalent; no rewrite of core writer.

## Phase 1 file scope
- mcias/audit_writer.py: exact original PR25 writer.
- tests/test_shared_audit_writer_phase1_pg.py: dedicated PostgreSQL-only tests on a controlled synthetic database, using minimal test-owned tables.
- .github/workflows/shared-audit-writer-phase1-pg.yml: disposable PostgreSQL 16 CI runner, no Alembic.
- docs/DG-001_SHARED_AUDIT_WRITER_PHASE1_AR.md: audit worklog, API contract, Phase 2 design and handoff.
No contracts, UI, migration, models.py, app.py, auth.py, tenant.py, or PR28 code imported.

## API contract (unchanged Phase 1)
- write_event(db, *, actor, organization_id, action, resource_type, resource_id, outcome, details=None): stages event and flushes within caller-owned transaction; caller alone owns commit/rollback. Use success with business transaction.
- record_outcome_independent(bind, *, actor_id, organization_id, action, resource_type, resource_id, outcome, details=None): requires trusted active actor matching tenant, caller must first rollback business transaction, then writer owns a separate session/commit for denial/error. Failure propagates. DO NOT use for successful business operations.
- Current writer permits success/denied/error values in both entrypoints; role-specific restrictions are contractual, not enforced in Phase 1. No dedicated anonymous API, unknown-commit resolver or retry guarantee exists yet.
- For HTTP 403, single request transaction owner must persist exactly once after rollback. PR28 integration remains separate and untouched.
- HTTP 409 requires separate categorized policy. Unexpected runtime errors require rollback and safe exception propagation; general central event handling not introduced in Phase 1.

## Proposed Phase 2 contract, NOT IMPLEMENTED
- request_attempt_id: server-generated UUID for every incoming HTTP request; client-provided ids cannot override it; propagated through request context. A retry creates a fresh request_attempt_id even when operation_id repeats.
- event_id: stable generated event identifier, reused for resolution. Proposed unique database constraint on (request_attempt_id, event_type) for single-event-per-attempt types; event_id uniqueness. Multiple distinct attempts must create distinct events. This is NOT guaranteed before database schema and tests.
- UNKNOWN: a lost connection during commit does not prove rollback. Never automatically insert a replacement event. Reconnect and reconcile by stable event_id; preserve UNKNOWN if uncertain. Avoid new event id on retry, verify database behavior under real fault injection.
- Anonymous denial: actor_id NULL only after source provenance, retention, access control and security reader policies are approved. Never invent user or tenant. No anonymous event write path introduced yet.
- Safe fields: action/event_type and resource_type finite server-defined enums; resource_id validated opaque identifier only; actor_id/organization_id trusted server state; reason_code predefined enum; details typed allowlist; never patient, family, diagnoses, prescriptions, notes, prices tied to patients, medical documents, credentials, raw SQL parameters or free text.
- Persistent columns and migration: evaluate required changes against latest main; no models.py changes or Alembic migration in Phase 1. L1 must establish deterministic safe target selection before any future migration.
- Potential P0 blockers: no database-enforced dedupe/correlation, unknown commit resolution, anonymous security event storage and complete field sanitization; do not claim Phase 1 supplies these protections.

## PostgreSQL acceptance scope
Phase 1 tests test exact original behavior, rollback and independent commit, actor and tenant checks, allowlist, and invalid fields. CI must run on disposable local PostgreSQL 16 with MCIAS_AUDIT_PHASE1_ALLOW=YES, URL ending /mcias_audit_phase1, and fresh empty tables. Tests never use production data or migration.
Phase 2 must add actual PostgreSQL failure injection at flush and commit (including ambiguous network failure), tenant and privacy probes, concurrent idempotency race and HTTP integration. Mocked exceptions do not substitute these tests.

## DG-001 handoff / rollback
Before next action: verify exact latest SHA and all workflow conclusions for this branch; check git hash-object of audit_writer.py equals source blob; inspect diff against main to confirm narrow scope. Record actual PostgreSQL CI status; never report scheduled or skipped test as executed PASS.
Rollback before merge: leave branch unmerged; no change to main or source PRs; branch can be closed only on separate approval. No production deployment or database migrations. Stop after Phase 1 independent review; require explicit Phase 2 authorization.
