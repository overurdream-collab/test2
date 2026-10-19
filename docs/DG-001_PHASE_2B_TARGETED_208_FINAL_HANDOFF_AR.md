# DG-001 — FINAL SEMANTIC CLOSURE: targeted 208-row ledger and handoff
Date 2026-10-20. Scope: source review, evidence-only scripts, documentation; no production code, migrations, merges, deploys or Phase3.
Original PR29 HEAD: 703e6536d3bac93da61492413c6d415815d3235c.
Original inventory artifact ID 12224321555; original classification artifact ID 12224188099; previous 1170-row evidence retained and updated in place.
Source SHA snapshots unchanged: main b69defa2f621458ef44d790b510840307a81009a, PR25 a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1, PR28 65bbddc1ae95aed22e157774f600a296a6e43926, PR29 baseline f9a0d126f33e8749e333166a2fc6c8d3a176dfc1.

## Targeted semantic ledger outcome
The existing evidence ledger docs/shared_audit_semantic_evidence/semantic_match_resolution.csv has 1170 rows with original IDs, SHA/file/line/function, source references, semantic state and explanation.
A targeted source check of the previous 208 unresolved rows was executed by scripts/resolve_remaining_208.py in GitHub Actions; all 208 now have a row-level evidence classification; the first run stopped on a source-snippet mismatch in test SQL and preserved records, then a fail-safe correction continued with explicit exceptions for multiline AST SQL. This did NOT rerun the original inventory.
Final current summary docs/shared_audit_semantic_evidence/semantic_closure_summary.json:
- processed 1170; resolved row labels 1170; unresolved row labels 0; original 208 resolved in two passes (202 followed by 6).
- classes: reference-only 175; transaction-owner local 218; audit consumer/query 228; non-audit 8; tests/fixture 541.
- zero source-unavailable files.
- resolved per ref: main 255/255; PR25 323/323; PR28 292/292; PR29 baseline 300/300.
- Evidence-limited distinction: a resolved row does not prove a complete cross-function HTTP-to-writer call chain. The older audit_consumer_matrix.csv contains 152 reference/function entries and 131 function-local owner verifications. **21 matrix rows still require complete entry-point/actor/tenant/transaction tracing**. Preserve this blocker rather than declaring overall semantic inventory READY on row labels alone.

## Source verification of last six
- 4 x preflight_g9.py:check_postgres_role line119: SQL has_table_privilege on audit_log DELETE checks permissions, no audit event persistence (one row in each pinned ref).
- PR25 workspace_api.py:activity_history line117: resource_type audit_log inside direct AuditLog(activity_read_denied) constructor line116, db.commit line119; corresponds to same consumer, not an additional event.
- PR28 app.py:get_db line67: record_denial_after_rollback(engine,exc) follows session.rollback() line64 and delegates to denial_events.py independent writer; actual HTTP transaction owner for typed AuthorizationDenied only.

## Future integration defects, not changed now
CONFIRMED: auth.require_permission, tenant.require_organization, governance.deny in main commit before 403; dirty business writes may be committed.
CONTRACT: PR25 create_contract records 409 reference_conflict as denied; mismatch with business conflict policy.
INTEGRATION RISK: PR25 endpoint-level rejection writer plus PR28 HTTP owner can duplicate 403 only if later combined; not proven duplicate across isolated branches.
PRIVACY/COMPATIBILITY: existing reference/G6/G8 details outside Phase2A allowlist; source IDs and anonymous technical rate limit/rotation need policy.
DESIGN PENDING: durable UNKNOWN reconciliation journal, request_attempt_id DB uniqueness, exactly-once not implemented.
Read-only source investigation of ingestion, claims, MFA, reporting, retention, Audit Policy, contract clauses and CLI is documented in docs/DG-001_PHASE_2B_FINAL_CONSUMER_SEMANTIC_HANDOFF_AR.md.

## Independent acceptance decision
MATCH LEDGER COMPLETE at line classification level. **FULL SEMANTIC CALL-PATH INVENTORY NOT YET READY** until the 21 matrix entries with unverified entrypoint/actor/tenant/owner chains have full source evidence or are shown non-operational. No promise of runtime correctness from static analyses. The earlier 208 unresolved match IDs are resolved; unresolved call paths are a distinct acceptance blocker.
No changes to audit_writer.py, audit_contract.py, tests, models, Alembic, main, PR25, PR28 or L1.
HANDOFF: audit_consumer_matrix.csv entries with status UNRESOLVED are precise next targets; expand source traces, preserve source refs and adjust matrix only with evidence. Do not start Phase3.
