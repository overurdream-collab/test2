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
