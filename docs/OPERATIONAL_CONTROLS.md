# Operational controls implementation

Base: integrated candidate e611281e7eb9d3ea0548e8028921554feadddd92.
Branch: feat/mcias-operational-controls. No gate acceptance changes.

## Scope

No source_type migration/backfill: all current records are disposable synthetic test data in separate test databases. Production onboarding must start with a clean database. UUID primary keys remain unchanged; new seed public references use SYN-. Reserved permission codes remain unchanged.

## API rate limits

Atomic PostgreSQL upserts share quotas across workers: 100/minute per verified user and 1000/minute per client IP, fixed UTC minute windows. Limits cover matched API routes. Invalid tokens never create user buckets. Health and login/logout remain outside this middleware; login retains its existing five-failure/15-minute account lockout. Public demo availability and development bootstrap status are exempt; unknown routes retain 404 responses.

429 responses include Retry-After and no-store; storage failure returns 503 rather than bypassing the limiter. One audit event per exceeded scope/window bounds log volume. Tokens, raw IPs, clinical data and URLs are not logged. Caller-controlled Forwarded/X-Forwarded-For headers are not parsed by middleware. Configure the ASGI server's trusted proxy addresses explicitly; never trust '*' or untrusted public clients. A fixed-minute window may allow bursts across a minute boundary; this is not a rolling-window SLA.

Maintenance deletes operational buckets older than 24 hours, never audit logs. Runtime requires SELECT/INSERT/UPDATE/DELETE on api_rate_limit_buckets; it must not own schema objects or have audit mutation privileges. Retention worker needs scoped SELECT and INSERT audit privileges, not UPDATE/DELETE. Provision permissions through the existing governed role process; no seed creates production privileges.

## Seed CLI

```sh
export MCIAS_ENVIRONMENT=development
# MCIAS_E2E_DATABASE_URL must name a PostgreSQL database ending in _e2e.
python -m mcias.seed
python scripts/seed_workspace_e2e.py
python -m mcias.seed --count 10000 --output .e2e-output/performance-fixture.json
```

The CLI migrates and loads a validated versioned JSON dataset. UUIDv5 identities, dataset hash and audit receipt make repeats idempotent. Changing a loaded dataset/count requires a fresh database. Private output contains synthetic login credentials and is mode 0600; it must not be published. Credentials are excluded from the audit receipt. Metadata-only source fixtures have no original encrypted file and explicitly record that limitation; actual upload/evidence workflows use the existing browser workflow harness. All seeded claims remain held, without fabricated institutional approvals. For >1000 claims the loader omits report snapshots to avoid an unbounded reporting fixture.

Reset is explicit and destructive, only for development *_e2e databases:

```sh
python -m mcias.seed --reset-confirm EXACT_DATABASE_NAME
```

It drops/recreates the entire dedicated DB. It never disables immutability triggers or forces active-session termination. No public Seed API is exposed. The dataset uses one validated file rather than an arbitrary 15-file requirement; existing golden tests retain malformed/conflict/objection/security scenarios.

## Migration and performance coverage

0017_operational_limits creates atomic quota buckets. 0018_claim_query_indexes adds organization/service_date, organization/provider_code, organization/beneficiary_token indexes. Runtime migration preflight and tests now expect 0018.

Recorded EXPLAIN (ANALYZE, BUFFERS) on 10,000 synthetic claims:

| Filter | Before ms | After ms |
|---|---:|---:|
| organization/date | 1.944 | 0.095 |
| organization/provider | 1.287 | 0.080 |
| organization/beneficiary | 1.124 | 0.034 |

This is one local warm-cache engineering comparison, not an accepted production SLA. Fixture has one main institution and synthetic repeating providers/beneficiaries. Audit/report tables were empty: their proposed composites remain deferred until representative workloads exist. governance_events(case_id, version) already has a UNIQUE index; no duplicate was added. Benchmark script rolls temporary indexes back and exports only query plans.

## Verification

Local PostgreSQL 16.15 / Python 3.12: 334 tests passed (including 30 concurrent requests competing for five slots, seed idempotence, tenant archive isolation, encryption, permissions, append-only history and prior regressions), 14 dependency/configuration warnings. Node: 10 tests passed; four frontend modules passed syntax checks. Browser results are recorded separately in evidence; do not infer institutional acceptance.

Chromium additionally passed the actual upload/quarantine/import/audit-evidence/governance/report/objection workflow and the retention request form, with zero page errors. The local PostgreSQL archive worker completed a queued month with encrypted readback verification; this synthetic month contained zero historical events (non-empty isolation/encryption cases are covered by unit tests). Wheel built using --no-build-isolation and its seed/limiter/archive/UI assets were verified. Evidence is in docs/evidence/operational/.

## System-wide audit requirements addendum (approved scope; not implemented)
Follow [MCIAS unified inputs and audit requirements](MCIAS_UNIFIED_INPUTS_AUDIT_REQUIREMENTS_AR.md) §4. Every consequential human/AI/service action, denied attempt and export needs correlated immutable actor/tenant/time/outcome evidence, local encryption and sensitive-value minimization, permissioned historical lookup and export, tamper/failure/tenant isolation tests. Current rate limiting and existing audit tables alone are **not proof of full coverage**. No new retention or purge permission is granted.
