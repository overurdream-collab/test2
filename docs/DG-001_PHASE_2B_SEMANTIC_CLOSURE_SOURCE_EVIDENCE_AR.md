# DG-001 — Phase 2B semantic closure source-verified checkpoint
Status: PARTIAL — SPECIFIC UNRESOLVED PATHS. 2026-10-20.
Start HEAD PR29 210bfc8521bae515c6330495aef6dd2887fc262f; no reset.
Source SHAs: main b69defa2f621458ef44d790b510840307a81009a, PR25 a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1, PR28 65bbddc1ae95aed22e157774f600a296a6e43926, PR29 baseline f9a0d126f33e8749e333166a2fc6c8d3a176dfc1.
No code/model/migration changes. No source inventory or PostgreSQL re-runs.

## Confirmed source call-paths and owner
| Ref / Source | Evidence lines | Actual chain | Outcome |
|---|---|---|---|
| main auth.py:require_permission | 65–68 | guard -> db.add(AuditLog permission_denied) -> db.commit -> HTTP403 | CONFIRMED DEFECT: possible pending business writes committed |
| main tenant.py:require_organization | 7–11 | guard -> db.add(AuditLog tenant_access_denied) -> db.commit -> HTTP403 | CONFIRMED DEFECT: same shared transaction issue |
| main governance.py:deny | 7–10 | deny -> db.add(AuditLog governance_denied) -> db.commit -> HTTP403 | CONFIRMED DEFECT |
| main governance.py:activate_rule | 13–21 | modify status -> add AuditLog rule_activated -> db.commit | VERIFIED atomic success for this path |
| PR25 reference_api.py:create_contract | 99–126 | permission failure -> rollback -> independent audit via endpoint (403), business conflict 409 -> rollback -> independent denied audit | CONTRACT INCOMPATIBILITY 409 classified denied; future duplicate owner risk against PR28, not existing branch duplicate |
| PR28 app.py:get_db | 57–70 | dependency except -> session.rollback -> if AuthorizationDenied, record_denial_after_rollback -> independent writer -> rethrow | VERIFIED owner-only for typed exception, other HTTPException not audited by this handler |
| PR28 denial_events.py:record_denial_after_rollback | 15–33 | trusted actor/tenant guard -> record_outcome_independent() | VERIFIED independent handler |
| main governance_g6.py:append_event | 49–61,138–149 | kind member PERMISSIONS -> GovernanceEvent flush -> AuditLog 'g6_'+kind -> commit | VERIFIED function-local bounded kind and atomic success |
| main intelligence_service_g8.py:_append_event | 120–131,133–176 | AnalysisTaskEvent flush -> AuditLog 'g8_task_'+kind -> commit | VERIFIED locally, three concrete call sites |
| main audit_policy_lifecycle.py:enroll_grant/revoke_grant | 12–39,40–55 | add audit to same session and commit | VERIFIED source-level success; broader caller inventory open |
| main mfa_enrollment.py:begin_enrollment/confirm_enrollment | 21–69 | mutate MFAFactor/session tokens -> add AuditLog -> db.commit | VERIFIED local atomic business+audit intent |
| main rate_limits.py:check_limits | 25–52 | DB counter -> optional AuditLog(actor_id=NULL) -> commit | VERIFIED already-existing anonymous technical event outside Shared Audit Writer; separate from proposed policy |
  
## Dynamic event value closure from source
G6 PERMISSIONS literal enum: propose,approve,hold,reject,object,request_reaudit,link_reaudit (governance_g6.py:15–23); append_event validates membership at line 50. All seven derived audit action names match 'g6_'+kind. It validates reason_code by syntax only (56–60), not a closed semantic enum, so risk of opaque sensitive values remains; trace API entry and payload provenance.
G8: direct _append_event callers test_task:142 (tested), activate_task:164 (activated), deactivate_task:175 (deactivated). Three 'g8_task_'+kind results bounded in inspected functions, but independent whole-repository caller search still needs complete closure.
  
## Open semantic call paths
1. Exhaustive parent call edges for direct AuditLog in Audit Service, all ingestion modules, Claim Batches, MFA CLI/recovery/rotation, G7, Retention, Reference Service, Input Clauses PR25, seed/CLI; require source line evidence of HTTP/service/job/CLI provenance, business owner and audit owner.
2. Link every production-relevant classification row from original 1170-match Artifact and especially all `requires_full_source_review=YES` records to a resolved chain or a precisely enumerated unresolved result. Existing category assignment CSV is NOT proof of resolution.
3. SQLAlchemy event listeners, indirect ORM Session.add + dynamic dispatch, SQL text() / exec_driver_sql() for audit-related transactions: still require verified positive/negative source evidence.
4. Distinguish 409 business_conflict pending design from 403, ensure no automatic denial classification; UNKNOWN durable journal ownership pending, not implemented.
5. Phase2A drops legacy details keys for G6/G8/reference and possible privacy loss via identifiers; need per-consumer field provenance checks.
  
## Decision, handoff
PARTIAL — SPECIFIC UNRESOLVED PATHS, not ready for independent semantic inventory acceptance. Scope is documentation-only on PR29; no edits to audit_writer.py, audit_contract.py, app/auth/tenant, models, tests or Alembic. Source-verified defects may be planned later only by explicit separate implementation authorization. Do not claim completed 1170-line semantic source closure.
