# L2-SEC-001 — DG-001 Worklog
Date: 2026-10-18
Base main: b69defa2f621458ef44d790b510840307a81009a
Branch: fix/mcias-l2-denial-transaction-safety

## Baseline / evidence
Previous SQLite synthetic reproduction: FAIL for both denied guards; independent-transaction denial writer pattern: PASS. These were not PostgreSQL or original-function runs.
Existing L2 evidence retained outside this branch; do not rewrite historical failures.

## Decisions
The shared audit writer exists in draft PR #25, not in main. Do not duplicate it, cherry-pick another owner's work, or claim it is available to this branch. Integration remains BLOCKED.
A new isolated PostgreSQL regression test uses original guard functions and refuses non-local or non-_l2_e2e targets. It performs no migrations.
Before any final approval, implement the FastAPI request transaction-owner rollback and one denial audit event via PR #25's shared writer, with an event de-duplication contract.

## Current status
PARTIAL / BLOCKED. No safe PostgreSQL target verified. No final PASS. No merge or deploy.


## 2026-10-18 — Corrected regression
Commit 23be2dad4eae611a4a6b7c76ee455a866751183b: test checks independent session BEFORE rollback; uses only disposable L2-SYNTHETIC fixture; restores leaked baseline mutation after observation; absence of safe PostgreSQL is explicit FAIL/BLOCKED, not a skip/PASS. Original guard implementation remains unchanged, so expected original result on PostgreSQL is FAIL, but unexecuted. No PostgreSQL local tool/service confirmed. Shared writer remains only on PR #25. Do not claim completion.

## 2026-10-19 — PostgreSQL 16 RED proof and partial fix
Baseline RED: GitHub Actions run 39257009551 on SHA 7315b8f9f323737cbf9ac5da7721dfe042a037c0: two tests failed with 'original guard committed pending business update'; PostgreSQL 16.15 isolated service, migration and synthetic fixture completed. Historical RED log: https://github.com/overurdream-collab/test2/actions/runs/39257009551 .
Added dedicated L2 PostgreSQL workflow; standard unit suite does not require PostgreSQL and skips L2-only test outside dedicated gate (skip cannot constitute final security PASS).
Updated auth.py, tenant.py to emit AuthorizationDenied without commit, app.py get_db exception owner to rollback, denial_events.py delegates to PR #25 writer via lazy import. Writer absent in main: real integration BLOCKED. No copied writer, no modifications to PR #25. Runtime denial event recording without dependency raises, preventing false audit-success claims. Final integration, compatibility tests and Green CI pending.
