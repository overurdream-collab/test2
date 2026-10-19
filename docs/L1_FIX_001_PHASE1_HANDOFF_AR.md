# L1-FIX-001 — Phase 1 RED Tests — DG-001 Worklog & HANDOFF

Date: 2026-10-19 (Asia/Aden)
Owner: L1 Foundation Engineering
Branch: `fix/mcias-l1-alembic-target-safety`
Base main SHA (verified via direct GitHub fetch): `b69defa2f621458ef44d790b510840307a81009a`
Initial test commit: `61d8a8d558a2258abd382f19f367e0ac0a5f71df`
Gate: **PARTIAL — RED only, no implementation authorized**

## Goal / boundaries
Establish negative tests proving Alembic's current ambiguous migration-target selection, then stop. No changes to `alembic/env.py`, models, migrations, runtime config, existing golden tests, L2 code, PR #25 or #28. No database connection or migration. No merge/deployment.

## Files changed in this phase
- ADDED `tests/test_l1_alembic_target_red.py`: read-only extraction of the original selector function using Python AST, executes that function in a fake settings namespace. Never imports the Alembic module, calls `create_engine`, opens a socket, or runs a migration.
- ADDED this HANDOFF document. No other files intentionally changed.

## Historical T01–T06 — preserve unchanged evidence
Six prior characterization tests ran locally and passed (6 passed in 0.10s). They prove TEST URL priority, lack of production guard, empty TEST fallback, duplicate URL acceptance, malformed TEST passthrough, and absence of trusted-target verification. They do NOT show safety acceptance and are NOT executed again by this phase's GitHub test file.

## Actual local RED reproduction — deliberately NOT exact uploaded test file
A separate local reproduction of the same original function body, using fake URLs and fake settings, ran under pytest with **6 failed, 2 passed in 0.10s; exit 1**. All six failed because `pytest.raises(ValueError)` saw **DID NOT RAISE**, indicating the selector permits insecure cases. Two legitimate URL selection cases passed.
This is an accurate local reproduction, NOT evidence that the uploaded full ten-test suite ran. That full suite and exact SHA CI are **NOT RUN / BLOCKED** pending safe test environment / runner availability. No skip is counted as RED proof.

## New test contract
- PASS expected now: explicitly designated runtime-only, isolated test-only, online/offline both use selector, CI test-only operation.
- RED expected now: conflicting URLs, TEST override in production, missing URL, malformed URL, unapproved TEST label, implicit fallback from empty TEST.
- Selector is compiled from repo `alembic/env.py` and called directly, with fake `Settings`; Python `ast` is solely an extraction mechanism to avoid module-level Alembic execution.
- `MCIAS_MIGRATION_TARGET` is a *proposed* explicit selector, NOT existing behavior or approved final interface.

## CI compatibility
Current `.github/workflows/ci.yml`, `g8.yml`, `g9.yml` set `MCIAS_TEST_DATABASE_URL` for PostgreSQL jobs. `workspace.yml` configures `MCIAS_DATABASE_URL` and `MCIAS_E2E_DATABASE_URL`, with TEST for a separate pytest job. Preserve these valid paths in phase 2; do not rely on `CI=true` alone.

## Risks & dependencies
P0 ambiguous target selection; P0 unintended production target; P1 test-only selector must remain possible without a runtime URL; P1 run logs must not include credentials; P1 PR/branch CI may not trigger on only new tests because of workflow path filters. Future Shared Audit Writer migrations rely on the same selector but are explicitly excluded here.

## Next action / independent review
1. Verify final branch SHA, changed file list, exact GitHub CI run coverage.
2. Run exact new test module using an isolated local checkout, no DB connection; expect six RED and four green.
3. Supervisor decides whether to authorize phase 2; only then update `alembic/env.py` minimally, preserving old characterization evidence.
4. Phase 2 validation: fake-only tests then PostgreSQL 16 synthetic isolated tests, CI regression, transaction/restore checks.


## Phase 1 Verification — 2026-10-19 — exact ten-test content
- Verified remote branch HEAD before this documentation update: `600892aac331e78087ddfab6dd1f199a4589ce02`; main `b69defa2f621458ef44d790b510840307a81009a`.
- Attempted clean `git clone --depth 1 --branch fix/mcias-l1-alembic-target-safety`, but container DNS blocked `github.com` (`Could not resolve host`). Therefore this is NOT a git checkout.
- Reconstructed a clean isolated directory using the **complete test file and env.py text fetched from GitHub at the confirmed branch**; did not alter those contents. Exact command: `python -m pytest -q tests/test_l1_alembic_target_red.py`.
- Python pytest execution: **6 failed, 4 passed, 0 skipped, 0 errors, exit 1, 0.08s**. Six RED failures all `Failed: DID NOT RAISE <class 'ValueError'>` for:
  - `test_reject_ambiguous_two_urls_before_connection`
  - `test_reject_test_override_in_production`
  - `test_reject_missing_url`
  - `test_reject_malformed_test_url`
  - `test_reject_unapproved_test_database`
  - `test_reject_implicit_fallback_after_empty_test`
- Four PASS: `test_allow_explicit_runtime_only`, `test_allow_isolated_test_only`, `test_offline_online_share_same_selector_source`, `test_ci_contract_explicit_test_url_does_not_require_runtime`.
- No Alembic module imported by the tests, no engine or socket call, no database connection or migration. The test extracts only the original function body by AST; synthetic URLs and mock Settings only. Online/offline coverage is static source inspection, not live execution.
- GitHub Actions commit workflow query returned `[]` (limited to PR events) and combined status returned `[]`. This does **not** prove all Actions absent; full Actions push-run coverage remains UNVERIFIED. No CI result is counted.
- Preserve historical T01–T06 characterization `6 passed` separately; untouched. No test expectations changed.
- Phase 2 requires explicit approval; safest small fix: reject ambiguities and invalid/unapproved targets before online engine / offline context config, keeping authorized isolated CI path. Recheck workflow environment contracts first.
- Only documentation updated in this verification cycle. No changes to `alembic/env.py`, migrations, models, current tests, shared-audit branches, main, CI config.


## Phase 2 — LIMITED SECURITY FIX (2026-10-19)
- Authorized scope: Alembic target selection, test contracts, necessary CI environment fields, documentation. No model/schema/migration change.
- Verified pre-change main SHA `b69defa2f621458ef44d790b510840307a81009a`, branch SHA `1cad03d4c7286c6f3af1ce2b302971cdb54f8dcc`.
- Changes: `alembic/env.py` now requires explicit `MCIAS_MIGRATION_TARGET=test|runtime`. Test requires `MCIAS_ENVIRONMENT=test`, a full PostgreSQL+psycopg URL, loopback host, and approved synthetic database label; production test selection rejected. Different simultaneous runtime/test URLs rejected; identical aliases allowed only in explicit test mode for existing workspace CI. Failure codes do not include credentials.
- CI edits: `.github/workflows/{ci,g8,g9,workspace}.yml` test jobs explicitly define `MCIAS_ENVIRONMENT=test` and `MCIAS_MIGRATION_TARGET=test`. Their test URL values were retained.
- T01-T06 historical pre-fix evidence unchanged; ten original RED test assertions unchanged.
- **CRITICAL LIMITATION**: URL/role/loopback controls and environment opt-in are NOT independent proof of a PostgreSQL cluster's identity. A privileged local service or malicious environment could impersonate a test database. True identity attestation (e.g., controlled ephemeral service provisioning with an independent expected instance identity) and an end-to-end negative test remain REQUIRED before security acceptance.
- **VALIDATION BLOCKED**: local `git clone` failed with DNS error `Could not resolve host: github.com`; GitHub connector can fetch/write files but no full checkout or runnable PostgreSQL 16 service was available. Do not claim exact ten-test green, real PostgreSQL integration, or CI pass without run evidence.
- No migration, DB connection, main merge, deployment, Shared Audit change or PR #28 change.
- Gate: **PARTIAL / ACCEPTANCE BLOCKED** pending exact ten-test execution, CI runs on branch SHA, synthetic PostgreSQL 16 verification, and independent server identity controls.
- NEXT: independent engineering reviewer must inspect selector and CI deltas and approve a minimal attestation approach that does not modify existing migration files; confirm true CI statuses and build isolated test environment. Do not merge.


## Final verification cycle — 2026-10-19
- Verified branch HEAD `445e25bea51711e45da6da96ce71695189e405d2` and main HEAD `b69defa2f621458ef44d790b510840307a81009a` before changes.
- Direct clean `git clone` unavailable (DNS resolving github.com failed); rebuilt an isolated Python test fixture manually from the GitHub-fetched original selector and exact ten assertion contracts. Therefore NOT a successful Git checkout; only a faithful scoped local reproduction.
- Before minimal fix: `python -m pytest -q tests/test_l1_alembic_target_red.py`: **9 passed, 1 failed, 0 skipped**. Failure `test_reject_malformed_test_url` because SQLAlchemy `make_url` raises `sqlalchemy.exc.ArgumentError` rather than a sanitized `ValueError`.
- Minimal authorized change: `alembic/env.py` imports/catches `sqlalchemy.exc.ArgumentError` and maps it to `ValueError("ALEMBIC_TARGET_INVALID")`. No assertion altered, no migration/schema/model change. Fix commit `1c81c91fa5482992bec871f4be00b6a8a2592a3f`.
- After fix, isolated Python reproduction: **10 passed, 0 failed, 0 skipped in 0.13s**; no DB engine, PostgreSQL connection, socket, or migration was invoked by the ten tests.
- IMPORTANT: No real PostgreSQL 16 on this container; no Docker or PostgreSQL executable. Genuine online migration, isolated server-identity proof, full reference regression, and all required CI are **BLOCKED / unverified**.
- Current selector does not independently attest server identity. Environment variables, host=loopback, and database name alone cannot guarantee a synthetic server or protect against locally redirected endpoints. This remains a P0 acceptance blocker.
- CI query on prior SHA returned empty arrays; do not misinterpret as success or failure. Recheck final SHA.
- Remaining risk: validation with invalid IP hostname may produce `ValueError` safely; no production isolation claim, no merge permission.
- Recommendation: **BLOCKED** pending isolated PostgreSQL 16 identity attestation, executed migration, reference regression and same SHA CI.
- Next action: independent engineering review and CI execution on a controlled ephemeral service. Keep separate ownership of Shared Audit Writer.


## 2026-10-19 — Isolated CI operational-verification gate (DG-001)
- Baseline checked before changes: branch `93ddc0075f0a83f82b4ffe4eff1a5ba4bf0afbcb`; main `b69defa2f621458ef44d790b510840307a81009a`.
- NEW `.github/workflows/l1-alembic-target-isolated.yml` on branch push and matching PR changes; explicitly runs exact ten historical tests from Actions checkout before any database provisioning.
- Uses temporary random DB password, PostgreSQL 16 disposable container, private Docker internal network and host-only bound TCP port, validates container ID/image/running state and host binding via Docker inspect. Builds target URL only after verification from runner-controlled values; exposes no production secret or environment URL input for these verification steps.
- Tests rejection with selector-only test, runs offline SQL generation, then online `alembic upgrade head` and PostgreSQL/reference/restore regression on disposable container; container/network cleanup `always()`.
- Last CI workflow adjustment commit `41247cbda4aac70c056f7c9ff54cb7aa77b35f04`.
- CRITICAL: workflow creation IS NOT evidence of execution. GitHub workflow-run query and commit status were empty on immediate check; the provider query omits some push runs. Real CI runs, PostgreSQL 16 image ID/check outputs, migration logs, and reference test results are NOT VERIFIED. Do not advertise PASS.
- Local host lacks Docker/psql and `git ls-remote` failed DNS for github.com; cannot independently run real PostgreSQL migration in this cycle.
- Existing T01-T06 and exact ten test assertions untouched. No changes to `alembic/env.py`, existing migrations, models, main, PR #25/#28/#29, Shared Audit, deployment.
- Independent identity guarantee boundary: newly created Docker container ID, image and network give independent provenance within the trusted GitHub-hosted job, but do not defend against compromised runner, CI definition, Docker daemon or adversarial job privileges. Runtime's selector alone still cannot attest server identity.
- G1-G7, G8, G9, Enterprise full independent reference gates on this final SHA remain UNVERIFIED (workflow path filters may not trigger). Gate: **BLOCKED / NO MERGE**.
- NEXT: obtain completed run ID/logs for isolated L1 workflow and same-SHA reference gates; examine failed step and adjust only proven defect, re-run; record exact SHA. Require independent approval before merge.
