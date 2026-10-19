# DG-001 — Shared Audit Phase 2B — Final Remaining Semantic Verification
Date: 2026-10-20. **Status: CONSUMER INVENTORY COMPLETE — READY FOR INDEPENDENT INVENTORY REVIEW ONLY**.
This supersedes the earlier 208-match / 21-matrix-row unresolved checkpoints; prior DG-001 files remain unchanged as historical evidence.

## Source refs and scope
Starting PR29 HEAD 703e6536d3bac93da61492413c6d415815d3235c; pinned source snapshots:
main b69defa2f621458ef44d790b510840307a81009a
PR25 a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1
PR28 65bbddc1ae95aed22e157774f600a296a6e43926
PR29 baseline f9a0d126f33e8749e333166a2fc6c8d3a176dfc1.

## Closed evidence
Original automation was accepted and NOT rerun for the purposes of analysis: 844 Python-file appearances and 1170 matches, artifact 12224321555. The source-anchored ledger remained at docs/shared_audit_semantic_evidence/semantic_match_resolution.csv; only the 208 previously unresolved rows were targeted, first 202 and then the remaining six. Final counts: 1170 total, 1170 classified, 0 unmatched/unresolved, 0 source-unavailable; main 255/255; PR25 323/323; PR28 292/292; PR29 baseline 300/300.
Final classes: 228 audit consumer/query matches, 218 local transaction-owner matches, 8 non-audit, 541 test or fixture and 175 reference-only.
Classification is per original match, NOT per distinct consumer.

Matrix at docs/shared_audit_semantic_evidence/audit_consumer_matrix.csv contains 152 reference/function entries:
131 VERIFIED_FUNCTION_LOCAL (transaction/bounded event evidence within function), 13 VERIFIED (explicit targeted call-chain evidence), 8 NOT_APPLICABLE (models declaration, writer docstring or acceptance test), 0 UNRESOLVED.
**Limit:** 131 VERIFIED_FUNCTION_LOCAL records are proved only at the source-function level, not independently proven end-to-end runtime behavior from each HTTP entry. This is an analytical inventory claim, not evidence of operational readiness, exactly-once, or successful UNKNOWN recovery.
Classified G6 kind list: propose,approve,hold,reject,object,request_reaudit,link_reaudit; G8 _append_event known callers: tested,activated,deactivated. Multi-branch duplicates counted as distinct reference appearances.

## Six last source-specific closures
- mcias/preflight_g9.py:check_postgres_role line119 in four references: SQL has_table_privilege on audit_log DELETE is a read-only privilege assertion, not event mutation.
- PR25 mcias/workspace_api.py:activity_history line117: `resource_type="audit_log"` is metadata inside AuditLog(activity_read_denied) created line116, committed line119; one event.
- PR28 mcias/app.py:get_db line67: `record_denial_after_rollback(engine,exc)` follows session.rollback line64; delegates to denial_events independent writer and reraises typed AuthorizationDenied.

## Known defects deferred, not fixed
CONFIRMED DEFECT: main auth.require_permission, tenant.require_organization and governance.deny commit prior to 403, potentially committing other pending changes.
CONTRACT INCOMPATIBILITY: PR25 HTTP409 reference conflict recorded as denied.
INTEGRATION RISK ONLY: future PR25 endpoint denial + PR28 central HTTP owner could double-write upon integration, not proven current defect.
PRIVACY: legacy reference, G6 and G8 details may be omitted by Phase2A allowlist; actor/tenant provenance and PII restrictions still need runtime integration tests.
DESIGN PENDING: durable request_attempt_id uniqueness, UNKNOWN committed ACK-loss settlement, anonymous technical events policy. No exactly-once claim.

## Evidence links and handoff
Targeted verification scripts:
- scripts/resolve_remaining_208.py
- scripts/finalize_consumer_matrix_21.py
Artifacts:
- docs/shared_audit_semantic_evidence/semantic_match_resolution.csv
- docs/shared_audit_semantic_evidence/audit_consumer_matrix.csv
- docs/shared_audit_semantic_evidence/semantic_closure_summary.json
- docs/shared_audit_semantic_evidence/targeted_208_resolution.md
Existing broader traces at docs/DG-001_PHASE_2B_FINAL_CONSUMER_SEMANTIC_HANDOFF_AR.md and call_path_evidence.md.
No application code changes, no model/Alembic changes, no PostgreSQL connection for this targeted analysis. GitHub Actions may trigger from documentation/source evidence commits; passing CI does not grant production acceptance.
**Handoff:** Independent supervisor verifies 1170 row IDs, final matrix statuses, exact source SHA/line anchors, and checks limitations. Operational defects remain backlog and require independent Phase3 scoped authorization. NO MERGE / DEPLOY / MIGRATION.
