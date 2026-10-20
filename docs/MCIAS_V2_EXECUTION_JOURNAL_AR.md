# MCIAS v2.0 — Execution Journal (CAI-01 isolated main-baseline work)

This file contains **only this isolated CAI-01 branch's new events**. PR #23 independently owns a larger unmerged project journal; integrate through AI CTO review, do not overwrite it.

### HANDOFF-20261021-001 — CAI-01 read-only source scope preflight
- Scope: Add pure G2 extracted-record preflight and synthetic tests; **no** G2/G3/G4/G5 existing code, schema, API, financial policy, human decision, or Shared Audit Writer changes.
- Why: CAI-01 P0 input sheet/summaries double-count risk in G4 staging; prevent false batch acceptance without an explicit source scope and verifiable row accounting.
- Files: `mcias/claims_batch_preflight.py`; `tests/test_cai01_batch_preflight.py`; `docs/CAI01_CLAIMS_INTEGRATION_READINESS_AR.md`; `docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md`; `docs/MCIAS_V2_CURRENT_STATE_AR.md`.
- Tests: `python -m pytest -q tests/test_cai01_batch_preflight.py` (12 passed in disposable local sandbox against baseline-equivalent parser/normalizer copies); repository CI on exact new GitHub SHA PENDING.
- Result: PENDING_CI; synthetic local unit checks 12 PASS; **not** a claims E2E or financial/production acceptance.
- Risks: workbook sheet index alone is not signed identity, Arabic header mapping absent, preflight not yet wired to G4, CI pending, global journal/current-state overlaps unmerged PR #23 and needs coordinated merge resolution.
- Next: CAI-01 to verify exact PR HEAD and G1–G7/unit/PG CI; then AI CTO decides governed worksheet/column binding contract for G4 with #25/A1.
- Handoff: read `docs/CAI01_CLAIMS_INTEGRATION_READINESS_AR.md`; confirm branch HEAD and run checks; remain isolated, do not merge/deploy or copy unapproved reference rates.

### HANDOFF-20261021-002 — CAI-01 mandatory output/rejection specification
- Scope: Add documentation-only mandatory dashboard, classification, deterministic proposed-rejection and human-approval contract; no runtime, schema, shared interface or policy change.
- Why: Owner-approved CAI-01 mandatory output requirements; ensure source-linked evidence, exclusive statuses and no automatic financial decisions.
- Files: `docs/MCIAS_CLAIMS_AUDIT_OUTPUT_CONTRACT_AR.md`, `docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md`, `docs/MCIAS_V2_CURRENT_STATE_AR.md`.
- Tests: NOT_RUN: documentation-only change; prior SHA `b550e232` unit 356 passed/19 skipped, PostgreSQL 144 passed; dependency-audit FAILED on Pillow 12.3.0 (8 CVEs), see run 39504263830. These are not new SHA test results.
- Result: NOT_RUN; specification pending independent AI CTO review.
- Risks: No signed rejection policy, no trusted death record, G3/G4/G5/G6/G7/G8 integration unverified; shared docs overlap unmerged #23; no financial acceptance.
- Next: CAI-01 requests independent specification review and coordination on data ownership and rejection authority before shared code changes.
- Handoff: Read `docs/MCIAS_CLAIMS_AUDIT_OUTPUT_CONTRACT_AR.md` and PR #31; keep draft/unmerged; do not infer CI or operational acceptance from documentation.
