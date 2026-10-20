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

### HANDOFF-20261021-003 — CAI-01 Phase 2 source contract and security triage
- Scope: Isolated design and verification of Excel-to-G4 source identity, sheet classification, reconciliation, G5 output categories and dependency-audit failure.
- Why: Owner-approved Phase 2; prevent non-claim sheets, silent source loss, duplicate amounts and tenant bypass before any shared integration.
- Files: `docs/CAI01_EXCEL_TO_G4_SOURCE_CONTRACT_AR.md`, `docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md`, `docs/MCIAS_V2_CURRENT_STATE_AR.md`.
- Tests: NOT_RUN for new contract (documentation-only). Existing HEAD 28a51ba: unit PASS, postgres-integration PASS, dependency-audit FAIL; reviewed failed job 118912523331.
- Result: DESIGN_ONLY. Pillow 12.3.0: eight pip-audit CVEs, fix listed 13.0.0; local mcias package skipped (not on PyPI). No shared dependency changes.
- Risks: G2 has no verified sheet-name/physical-row ledger; G4 stages all extracted rows; PR #25 unmerged; no E2E integration or trusted source approval.
- Next: AI CTO/owners review source manifest, row ledger, G4 filtering, event schema and Pillow remediation before any shared change.
- Handoff: Read `docs/CAI01_EXCEL_TO_G4_SOURCE_CONTRACT_AR.md` and PR #31; remain draft, no merge/deploy/automatic financial decisions.

### HANDOFF-20261021-004 — CAI-01 Output Contract Review Closure
- Scope: Append clarifications to existing output contract; beneficiary-not-found versus proved ineligibility, financial approval independence, integration ownership and unresolved policy sources.
- Why: Approved documentation-only independent review closure; avoid false deterministic rejection and ownership conflicts.
- Files: `docs/MCIAS_CLAIMS_AUDIT_OUTPUT_CONTRACT_AR.md`, `docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md`, `docs/MCIAS_V2_CURRENT_STATE_AR.md`.
- Tests: NOT_RUN; documentation-only. Existing tests not repeated. Previous verified CI unit PASS, postgres PASS, dependency-audit FAIL (Pillow 12.3.0, eight CVEs); new commit CI not yet assessed.
- Result: DOCUMENTATION_REFINED; independent review PENDING; no new implementation.
- Risks: No approved institutional death source or final rejection rules; G3/G4/G5/G6/G7/G8, PR #25 and #29 shared contracts unapproved; dependency audit remains a separate open blocker.
- Next: AI CTO and independent owners review section 10 of output contract and approve integration ownership/contracts before implementation.
- Handoff: Continue from newest PR #31 HEAD, no reset; preserve existing Phase 2 design; no merge/deploy or automatic financial action.

### HANDOFF-20261021-005 — CAI-01 Phase 2 multi-batch verification and performance plan
- Scope: Extend existing Excel-to-G4 contract with multi-batch synthetic acceptance cases, G4 bounded import/resume design, security evidence and dependencies.
- Why: Owner request for multi-batch duplicate, tariff, cost-share, cap, family and scalability coverage without changing shared systems.
- Files: `docs/CAI01_EXCEL_TO_G4_SOURCE_CONTRACT_AR.md`, `docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md`, `docs/MCIAS_V2_CURRENT_STATE_AR.md`.
- Tests: NOT_RUN (documentation-only); existing PR #31 HEAD f11d696 unit PASS and PostgreSQL PASS, dependency-audit FAIL. Verified failed job 118914182878, eight Pillow 12.3.0 CVEs; no rerun.
- Result: DESIGN_COMPLETE_FOR_REVIEW, IMPLEMENTATION_BLOCKED pending G2/G4/Shared Audit owners and independent test execution.
- Risks: G2 physical-row coverage/approved sheet inventory unavailable; G4 stages all rows and reads full record set; no verified Excel→G4→G5 E2E; Pillow remediation pending.
- Next: AI CTO independent review; coordinate owners before changing shared files or dependencies.
- Handoff: Draft PR #31; preserve existing contracts; stop after documentation; no merge/deploy/automatic financial action.
