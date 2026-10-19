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
