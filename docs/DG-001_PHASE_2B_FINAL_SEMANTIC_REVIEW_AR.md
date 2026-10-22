# DG-001 — Phase 2B FINAL semantic classification — evidence, findings and HANDOFF
Status: PARTIAL / UNRESOLVED CALL PATHS, independent review not yet ready.
Baselines remain: main b69defa2f621458ef44d790b510840307a81009a; PR25 a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1; PR28 65bbddc1ae95aed22e157774f600a296a6e43926; PR29 f9a0d126f33e8749e333166a2fc6c8d3a176dfc1. Latest current branch HEAD must be reverified at handoff.
Original artifact run 39330289038, artifact 12224321555, SHA256 12891f2fa22bab9515aefd7f1119ea409442abe5560a5c22e92708983906bf6c.
Original: files.csv (844 rows), matches.csv (1170), summary.json, SUMMARY.md, inspected from extracted downloaded ZIP. Totals: main 206/255, PR25 215/323, PR28 213/292, PR29 baseline 210/300. Read failures zero.
Annotation script: scripts/classify_shared_audit_matches.py. CI: https://github.com/overurdream-collab/test2/actions/runs/39331322185 ; classification artifact ID 12224188099, artifact name shared-audit-semantic-classification, digest sha256:cfa7240bd0462dc0c9eb471c2c60d5305cba6f3ed87741f13b27c8e3b53e95a1.
Annotation output retains every original reference SHA, path, function, line, category and reason plus follow-up flag. Successful annotation means no CSV lines dropped, **NOT completed manual review of all execution paths**. The exported original evidence is not overwritten.

## Newly surfaced consumers beyond prior DG-001 matrix
Discovered in original source match CSV, with examples of actual direct AuditLog construction:
- main mcias/audit_policy_lifecycle.py:enroll_grant:36 and revoke_grant:51 — policy_grant_enrolled/revoked, service local commits.
- main mcias/audit_service.py:run_audit:79 — audit_snapshot_created with service commit.
- main mcias/bootstrap_mfa.py:provision_privileged_factor:25 — offline_mfa_bootstrap, CLI/administrative flow.
- main mcias/claim_batches.py:stage:45,resume:111,attach:132 — claim_batch_staged/resumed, claim_attachment_linked.
- main mcias/governance_g6.py:open_case:43,append_event:144 — g6_case_opened and dynamic 'g6_' + kind.
- main mcias/ingestion/orchestrator.py:ingest:53, ingestion/reprocessing.py:retry:38, ingestion/review.py:decide:21 — source_ingested/ingestion_reprocessed/ingestion_quarantine_reviewed.
- main mcias/intelligence_service_g8.py:create_task:72,_append_event:126,create_run:244 — g8_task_draft, dynamic g8_task_ + kind, g8_analysis_review_created; intelligence_review_g8.py:add_review:63 — g8_signal_review_recorded.
- main mcias/mfa_enrollment.py:begin_enrollment:35,confirm_enrollment:60; mfa_key_rotation.py:rotate_all_factors:26; mfa_recovery.py:replace_factor:60 — MFA lifecycle and offline technical actions, including nullable actor event.
- main mcias/rate_limits.py:check_limits:47 — rate-limit event actor may be NULL; requires anonymous event contract review.
- main mcias/reference.py:approve_contract:89 — contract_approved.
- main mcias/reporting_g7.py:create_snapshot:204 — g7_report_frozen.
- main mcias/retention.py:request_archive:27,run_archive:81 — retention audit.
- main mcias/seed/loader.py:load:97 — synthetic_seed_loaded in CLI/test utility.
- PR25 mcias/input_clause_service.py:create_draft:147,authorize_draft:214 — input_clause_draft_created / input_clause_version_activated.
- PR25 mcias/workspace_api.py:activity_history:116 — activity_read_denied in HTTP.
- PR25 mcias/reference_api.py:create_contract:110,122 and revise_contract:241 — direct independent writer calls.
- PR28 mcias/denial_events.py:record_denial_after_rollback:27 and app.py:get_db:67 — centralized HTTP 403, independent post-rollback.
- PR29 mcias/audit_writer.py:write_event:19 and record_outcome_independent:34 — shared writer and independent persistence.
These are source-level constructor/call observations, not complete entrypoint/transaction call graphs for each path.

## Semantic chains confirmed by targeted source inspection
1. main auth.py authenticate -> add SessionToken + AuditLog(login) -> db.commit; require_permission -> add AuditLog(permission_denied) -> db.commit -> HTTPException403; revoke_session -> mutate token + AuditLog(logout) -> db.commit. 403 business dirty write risk P0.
2. main tenant.py require_organization -> AuditLog(tenant_access_denied) -> db.commit -> HTTPException403. Business dirty write risk P0.
3. main governance.py deny -> AuditLog(governance_denied) -> db.commit -> HTTPException403; activate_rule -> mutate status + AuditLog(rule_activated) -> db.commit. P0 for denial.
4. main reference_service.py _audit(db,actor,action,kind,id,details) -> direct AuditLog; draft/tariff/enrollment service functions commit. The wrapper makes caller analysis essential and Phase2A typed details may omit provider_code, contract_id, category_id.
5. PR25 reference_service.py uses write_event for contract draft create/revise; PR25 reference_api.py independently writes denied events inside endpoints. PR28 get_db catches AuthorizationDenied, rolls back and calls denial_events.record_denial_after_rollback -> record_outcome_independent, then reraises. These are separate branches: duplicate 403 is a future integration risk, not proven present duplicate.
6. PR25 workspace_api.py activity_history -> denied AuditLog -> commit -> HTTP403; its reader uses join User scoped by actor's organization; historical null-actor security events excluded.
7. PR29 audit_writer.py stages success with db.flush inside caller transaction, independent denied/error opens Session and commits; new typed validation in audit_contract.py rejects arbitrary resource identifiers and drops unrecognized details.

## OPEN / unverified call paths — blockers to semantic closure
- Complete entrypoint chains for G6, G8, ingestion, MFA offline tooling, rate limits, retention, reporting, policy grants, all audited services and dynamic event name generation.
- Exact correspondence of transaction_boundary lines with audit constructor on same execution branch (classification marks candidates; line-level evidence insufficient). SQLAlchemy hooks, importlib, getattr and reflective dispatch across all source files require full-file AST/control-flow inspections.
- Actor/organization provenance, resource ID classification, error/rollback and 409/5xx semantics in those paths; privacy assessment per caller.
- Derived normalized consumer matrix with complete transaction owners and entrypoints for every actual consumer is not yet independently attested.
- Canonical business_conflict outcome or separate event type remains unresolved; durable journal/queue for UNKNOWN recovery remains unselected and untested.
- No claim of Exactly-once or operational approval. No production DB access or PostgreSQL retesting requested.

## Independent review gate
Inspect classification artifact line-by-line or by function group. Trace every direct constructor, writer call and relevant wrapper from complete source files; for transaction_candidate and dynamic events document parent callers and actual owner; enumerate what raw SQL touches versus tests/migrations; update matrix only on supported evidence. If any material path unknown, keep status PARTIAL. Do not merge, deploy, migrate or start Phase 3.

## Worklog and scope
This update writes only documentation, the offline read-only classifier script, and GitHub Actions supporting artifact reproduction on PR29. Original mcias/audit_writer.py, audit_contract.py, PostgreSQL tests, all model and Alembic files unchanged. No changes to main, PR25, PR28, L1.
