# DG-001 — INPUTS-FIRST Shared Audit owner handoff

Date: 2026-10-21. Scope: coordinated minimum implementation and synthetic PostgreSQL 16 verification only. Base PR #29 HEAD: `c7769edfdf6e287824ff7afbd8a74389547d7b53`. Work branch: `codex/inputs-first-shared-audit`. No merge, deployment, migration, force push or real patient data.

## Approved exchange contract

The existing `write_event(db, *, actor, organization_id, action, resource_type, resource_id, outcome, details)` API remains unchanged. G5 stages `action=claim_inputs_audited`, `resource_type=claim_entry`, `resource_id=ClaimEntry.id`, `outcome=success` in the same business transaction as its immutable `AuditSnapshot`. Success describes event recording, not financial approval.

Required typed details: `audit_snapshot_id`, `source_record_id`, `document_id` (canonical UUIDs), `source_sha256`, `policy_fingerprint` (SHA-256), the approved `audit_state`, and six `references`. Each reference contains only `family,id,version,status,evidence_ids,gaps`. The exact families come from G3's approved contract: beneficiary, contract, tariff, policy, caps, history. Missing references retain null identity/version and bounded gap codes. Unknown metadata is discarded; malformed required metadata fails closed. The four states are the existing contract strings `VERIFIED_MATCH`, `PROVEN_VIOLATION`, `UNRESOLVED_OR_MISSING_REFERENCE`, `AUDIT_NOT_POSSIBLE`; no parallel status model was added.

The writer verifies organization, claim, source-record/document/SHA, policy and audit state against existing persisted rows. It canonicalizes the immutable snapshot's G3 certificates and verifies every reference identity, version, status, source/authorization evidence UUID and gap code matches the event. Optional policy version must match the snapshot if supplied. It never reads or writes patient values into the event.

The event ID is UUID5 over the action, organization and immutable snapshot UUID. Atomic `INSERT ... ON CONFLICT DO NOTHING` uses the existing `audit_log` primary key. An identical retry returns the first event; changed correlation fails. A rollback removes the event with the business transaction. No schema change or second writer was introduced. This narrowly deduplicates one snapshot result and does not claim general request exactly-once or UNKNOWN/ACK-loss recovery.

## HTTP 429 diagnosis

The previous HTTP test executed 101 requests using real wall time while the actual limiter uses fixed-minute `(scope_hash,window_start)` buckets. Crossing the minute boundary legitimately creates a new bucket, so request 101 may be allowed. The new regression reads actual `RateLimitBucket` rows and proves the prior-minute user bucket contains 100 requests while the next-minute bucket contains 1. The HTTP test freezes only its wall clock, then verifies real IP/user buckets each contain 101 requests, one exceeded-user event is stored, forwarded headers do not create new identities, and HTTP 429/Retry-After/no-store remain intact. No limiter implementation, quota or security enforcement was changed.

## Verification and limits

Root coordinator executed the final real PG16 and regression command with **39 passed in 3.91 seconds** after snapshot-reference projection validation. An earlier run before the final correlation check passed 39 tests in 4.72 seconds. The synthetic PG tests verify commit/reopen, one persisted event on concurrent retries, rollback/retry, tenant/source rejection, reference substitution rejection and PHI exclusion. Contract and operational tests cover unchanged public signatures and fixed-minute behavior. Exact final result is recorded in the atomic journal entry below.

Command (synthetic connection supplied by the coordinator):

```sh
PYTHONPATH=. MCIAS_INPUTS_AUDIT_ALLOW=YES \
MCIAS_INPUTS_AUDIT_DATABASE_URL=postgresql+psycopg://postgres:synthetic-only@127.0.0.1:55432/mcias_inputs_audit \
/workspace/.venv/bin/python -m pytest -q tests/test_shared_audit_inputs_pg16.py tests/test_operational_controls.py tests/test_shared_audit_phase2a_contract.py
```

The local database is disposable, guarded by localhost, explicit consent, exact database name and server major version 16; no Alembic migration runs. Writer-owned tests use persisted synthetic claim/snapshot fixtures; the coordinator owns composed G2→G3→G4→G5 acceptance and latest-SHA CI. No CI URL is claimed before a real run is published. Shared Audit has no remaining local implementation blocker; full upstream reference completeness remains G3's responsibility and synthetic success does not grant institutional acceptance.
