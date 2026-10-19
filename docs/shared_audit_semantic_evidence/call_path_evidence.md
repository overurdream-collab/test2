# Phase 2B semantic call paths — source-anchored function-level evidence

This is conservative static source validation. An entry-point marked pending is NOT semantic closure.

| Ref | SHA | Function | Source audit lines | Commit/rollback tokens in function | Status |
|---|---|---|---|---|---|
| main | `b69defa2f621` | `mcias/audit_policy_lifecycle.py:enroll_grant` | 36 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/audit_policy_lifecycle.py:revoke_grant` | 51 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/audit_service.py:run_audit` | 79 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/auth.py:authenticate` | 46 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/auth.py:require_permission` | 66 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/auth.py:revoke_session` | 72 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/bootstrap_mfa.py:provision_privileged_factor` | 25 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/claim_batches.py:attach` | 132 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/claim_batches.py:resume` | 111 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/claim_batches.py:stage` | 45 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/governance.py:activate_rule` | 19 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/governance.py:deny` | 8 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/governance_g6.py:append_event` | 144 | db.commit(,db.flush( | UNRESOLVED |
| main | `b69defa2f621` | `mcias/governance_g6.py:open_case` | 43 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/ingestion/orchestrator.py:ingest` | 53 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/ingestion/reprocessing.py:retry` | 38 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/ingestion/review.py:decide` | 21 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/intelligence_review_g8.py:add_review` | 63 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/intelligence_service_g8.py:_append_event` | 126 | db.commit(,db.flush( | UNRESOLVED |
| main | `b69defa2f621` | `mcias/intelligence_service_g8.py:create_run` | 244 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/intelligence_service_g8.py:create_task` | 72 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/mfa_enrollment.py:begin_enrollment` | 35 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/mfa_enrollment.py:confirm_enrollment` | 60 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/mfa_key_rotation.py:rotate_all_factors` | 26 | db.commit(,db.rollback( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/mfa_recovery.py:replace_factor` | 60 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/models.py:<module>` | 49 | caller-owned/unknown | UNRESOLVED |
| main | `b69defa2f621` | `mcias/rate_limits.py:check_limits` | 47 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/reference.py:approve_contract` | 89 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/reference_service.py:_audit` | 11 | caller-owned/unknown | UNRESOLVED |
| main | `b69defa2f621` | `mcias/reporting_g7.py:create_snapshot` | 204 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/retention.py:request_archive` | 27 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/retention.py:run_archive` | 81 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/seed/loader.py:load` | 97 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| main | `b69defa2f621` | `mcias/tenant.py:require_organization` | 9 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/audit_policy_lifecycle.py:enroll_grant` | 36 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/audit_policy_lifecycle.py:revoke_grant` | 51 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/audit_service.py:run_audit` | 79 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/audit_writer.py:<module>` | 4 | caller-owned/unknown | UNRESOLVED |
| pr25 | `a9d23ddcf4b3` | `mcias/audit_writer.py:record_outcome_independent` | 58 | independent.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/audit_writer.py:write_event` | 37 | db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/auth.py:authenticate` | 46 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/auth.py:require_permission` | 66 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/auth.py:revoke_session` | 72 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/bootstrap_mfa.py:provision_privileged_factor` | 25 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/claim_batches.py:attach` | 132 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/claim_batches.py:resume` | 111 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/claim_batches.py:stage` | 45 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/governance.py:activate_rule` | 19 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/governance.py:deny` | 8 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/governance_g6.py:append_event` | 144 | db.commit(,db.flush( | UNRESOLVED |
| pr25 | `a9d23ddcf4b3` | `mcias/governance_g6.py:open_case` | 43 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/ingestion/orchestrator.py:ingest` | 53 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/ingestion/reprocessing.py:retry` | 38 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/ingestion/review.py:decide` | 21 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/input_clause_service.py:authorize_draft` | 214 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/input_clause_service.py:create_draft` | 147 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/intelligence_review_g8.py:add_review` | 63 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/intelligence_service_g8.py:_append_event` | 126 | db.commit(,db.flush( | UNRESOLVED |
| pr25 | `a9d23ddcf4b3` | `mcias/intelligence_service_g8.py:create_run` | 244 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/intelligence_service_g8.py:create_task` | 72 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/mfa_enrollment.py:begin_enrollment` | 35 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/mfa_enrollment.py:confirm_enrollment` | 60 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/mfa_key_rotation.py:rotate_all_factors` | 26 | db.commit(,db.rollback( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/mfa_recovery.py:replace_factor` | 60 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/models.py:<module>` | 49 | caller-owned/unknown | UNRESOLVED |
| pr25 | `a9d23ddcf4b3` | `mcias/rate_limits.py:check_limits` | 47 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/reference.py:approve_contract` | 89 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/reference_api.py:create_contract` | 110,122 | db.rollback( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/reference_api.py:revise_contract` | 241 | db.rollback( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/reference_service.py:_audit` | 11 | caller-owned/unknown | UNRESOLVED |
| pr25 | `a9d23ddcf4b3` | `mcias/reference_service.py:create_draft` | 46 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/reference_service.py:revise_contract_draft` | 81 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/reporting_g7.py:create_snapshot` | 204 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/retention.py:request_archive` | 27 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/retention.py:run_archive` | 81 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/seed/loader.py:load` | 97 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/tenant.py:require_organization` | 9 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `mcias/workspace_api.py:activity_history` | 116 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr25 | `a9d23ddcf4b3` | `scripts/check_contracts_acceptance.py:<module>` | 387 | caller-owned/unknown | UNRESOLVED |
| pr28 | `65bbddc1ae95` | `mcias/audit_policy_lifecycle.py:enroll_grant` | 36 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/audit_policy_lifecycle.py:revoke_grant` | 51 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/audit_service.py:run_audit` | 79 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/audit_writer.py:<module>` | 4 | caller-owned/unknown | UNRESOLVED |
| pr28 | `65bbddc1ae95` | `mcias/audit_writer.py:record_outcome_independent` | 58 | independent.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/audit_writer.py:write_event` | 37 | db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/auth.py:authenticate` | 46 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/auth.py:revoke_session` | 73 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/bootstrap_mfa.py:provision_privileged_factor` | 25 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/claim_batches.py:attach` | 132 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/claim_batches.py:resume` | 111 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/claim_batches.py:stage` | 45 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/denial_events.py:record_denial_after_rollback` | 27 | caller-owned/unknown | UNRESOLVED |
| pr28 | `65bbddc1ae95` | `mcias/governance.py:activate_rule` | 19 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/governance.py:deny` | 8 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/governance_g6.py:append_event` | 144 | db.commit(,db.flush( | UNRESOLVED |
| pr28 | `65bbddc1ae95` | `mcias/governance_g6.py:open_case` | 43 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/ingestion/orchestrator.py:ingest` | 53 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/ingestion/reprocessing.py:retry` | 38 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/ingestion/review.py:decide` | 21 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/intelligence_review_g8.py:add_review` | 63 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/intelligence_service_g8.py:_append_event` | 126 | db.commit(,db.flush( | UNRESOLVED |
| pr28 | `65bbddc1ae95` | `mcias/intelligence_service_g8.py:create_run` | 244 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/intelligence_service_g8.py:create_task` | 72 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/mfa_enrollment.py:begin_enrollment` | 35 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/mfa_enrollment.py:confirm_enrollment` | 60 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/mfa_key_rotation.py:rotate_all_factors` | 26 | db.commit(,db.rollback( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/mfa_recovery.py:replace_factor` | 60 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/models.py:<module>` | 49 | caller-owned/unknown | UNRESOLVED |
| pr28 | `65bbddc1ae95` | `mcias/rate_limits.py:check_limits` | 47 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/reference.py:approve_contract` | 89 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/reference_service.py:_audit` | 11 | caller-owned/unknown | UNRESOLVED |
| pr28 | `65bbddc1ae95` | `mcias/reporting_g7.py:create_snapshot` | 204 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/retention.py:request_archive` | 27 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/retention.py:run_archive` | 81 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr28 | `65bbddc1ae95` | `mcias/seed/loader.py:load` | 97 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/audit_policy_lifecycle.py:enroll_grant` | 36 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/audit_policy_lifecycle.py:revoke_grant` | 51 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/audit_service.py:run_audit` | 79 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/audit_writer.py:<module>` | 4 | caller-owned/unknown | UNRESOLVED |
| pr29_baseline | `f9a0d126f33e` | `mcias/audit_writer.py:record_outcome_independent` | 47 | independent.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/audit_writer.py:write_event` | 26 | db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/auth.py:authenticate` | 46 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/auth.py:require_permission` | 66 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/auth.py:revoke_session` | 72 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/bootstrap_mfa.py:provision_privileged_factor` | 25 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/claim_batches.py:attach` | 132 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/claim_batches.py:resume` | 111 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/claim_batches.py:stage` | 45 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/governance.py:activate_rule` | 19 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/governance.py:deny` | 8 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/governance_g6.py:append_event` | 144 | db.commit(,db.flush( | UNRESOLVED |
| pr29_baseline | `f9a0d126f33e` | `mcias/governance_g6.py:open_case` | 43 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/ingestion/orchestrator.py:ingest` | 53 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/ingestion/reprocessing.py:retry` | 38 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/ingestion/review.py:decide` | 21 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/intelligence_review_g8.py:add_review` | 63 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/intelligence_service_g8.py:_append_event` | 126 | db.commit(,db.flush( | UNRESOLVED |
| pr29_baseline | `f9a0d126f33e` | `mcias/intelligence_service_g8.py:create_run` | 244 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/intelligence_service_g8.py:create_task` | 72 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/mfa_enrollment.py:begin_enrollment` | 35 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/mfa_enrollment.py:confirm_enrollment` | 60 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/mfa_key_rotation.py:rotate_all_factors` | 26 | db.commit(,db.rollback( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/mfa_recovery.py:replace_factor` | 60 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/models.py:<module>` | 49 | caller-owned/unknown | UNRESOLVED |
| pr29_baseline | `f9a0d126f33e` | `mcias/rate_limits.py:check_limits` | 47 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/reference.py:approve_contract` | 89 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/reference_service.py:_audit` | 11 | caller-owned/unknown | UNRESOLVED |
| pr29_baseline | `f9a0d126f33e` | `mcias/reporting_g7.py:create_snapshot` | 204 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/retention.py:request_archive` | 27 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/retention.py:run_archive` | 81 | db.commit( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/seed/loader.py:load` | 97 | db.commit(,db.flush( | VERIFIED_FUNCTION_LOCAL |
| pr29_baseline | `f9a0d126f33e` | `mcias/tenant.py:require_organization` | 9 | db.commit( | VERIFIED_FUNCTION_LOCAL |

## Remaining unresolved per source
- `b69defa2f621458ef44d790b510840307a81009a:mcias/audit_policy_api.py:30` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/audit_policy_api.py:41` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/claims_api.py:24` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/claims_api.py:27` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/governance_g6_api.py:32` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/governance_g6_api.py:44` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/ingestion/review.py:19` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/intelligence_g8_api.py:54` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/intelligence_g8_api.py:69` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/login_limits.py:37` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/mfa_recovery.py:22` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/preflight_g9.py:118` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/preflight_g9.py:119` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/rate_limits.py:58` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference.py:72` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference.py:73` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference.py:74` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference_api.py:91` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference_api.py:94` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference_service.py:36` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference_service.py:60` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference_service.py:69` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference_service.py:81` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference_service.py:110` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference_service.py:126` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference_service.py:146` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reference_service.py:167` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/reporting_g7_api.py:49` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:mcias/retention.py:21` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/retention.py:36` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/retention.py:37` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/retention.py:40` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/retention.py:41` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/retention.py:51` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/retention.py:52` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:mcias/seed/loader.py:30` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:scripts/benchmark_operational_indexes.py:42` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:scripts/check_integrated_workflow.py:80` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:scripts/check_integrated_workflow.py:172` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:scripts/check_integrated_workflow.py:206` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:scripts/check_retention_browser.py:80` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `b69defa2f621458ef44d790b510840307a81009a:scripts/retention_worker.py:23` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:scripts/retention_worker.py:24` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:scripts/retention_worker.py:25` — Audit identifier reference needs call path inspection
- `b69defa2f621458ef44d790b510840307a81009a:tests/test_g9_postgres.py:46` — Artifact source line does not match pinned git file
- `b69defa2f621458ef44d790b510840307a81009a:tests/test_postgres_integration.py:49` — Artifact source line does not match pinned git file
- `b69defa2f621458ef44d790b510840307a81009a:tests/test_postgres_integration.py:51` — Artifact source line does not match pinned git file
- `b69defa2f621458ef44d790b510840307a81009a:tests/test_postgres_integration.py:64` — Artifact source line does not match pinned git file
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/audit_policy_api.py:30` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/audit_policy_api.py:41` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/audit_writer.py:27` — Source and pinned line verified
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/audit_writer.py:45` — Source and pinned line verified
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/claims_api.py:24` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/claims_api.py:27` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/governance_g6_api.py:32` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/governance_g6_api.py:44` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/ingestion/review.py:19` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/intelligence_g8_api.py:54` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/intelligence_g8_api.py:69` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/login_limits.py:37` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/mfa_recovery.py:22` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/preflight_g9.py:118` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/preflight_g9.py:119` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/rate_limits.py:58` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference.py:72` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference.py:73` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference.py:74` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference_api.py:93` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference_api.py:96` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference_service.py:110` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference_service.py:119` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference_service.py:131` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference_service.py:160` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference_service.py:176` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference_service.py:196` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reference_service.py:217` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/reporting_g7_api.py:49` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/retention.py:21` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/retention.py:36` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/retention.py:37` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/retention.py:40` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/retention.py:41` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/retention.py:51` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/retention.py:52` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/seed/loader.py:30` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/workspace_api.py:117` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/workspace_api.py:123` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/workspace_api.py:126` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:mcias/workspace_api.py:127` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:scripts/benchmark_operational_indexes.py:42` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:scripts/check_contracts_acceptance.py:410` — Artifact source line does not match pinned git file
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:scripts/check_contracts_acceptance.py:411` — Artifact source line does not match pinned git file
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:scripts/check_integrated_workflow.py:80` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:scripts/check_integrated_workflow.py:172` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:scripts/check_integrated_workflow.py:206` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:scripts/check_retention_browser.py:80` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:scripts/retention_worker.py:23` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:scripts/retention_worker.py:24` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:scripts/retention_worker.py:25` — Audit identifier reference needs call path inspection
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:tests/test_g9_postgres.py:46` — Artifact source line does not match pinned git file
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:tests/test_postgres_integration.py:49` — Artifact source line does not match pinned git file
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:tests/test_postgres_integration.py:51` — Artifact source line does not match pinned git file
- `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1:tests/test_postgres_integration.py:64` — Artifact source line does not match pinned git file
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/app.py:64` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/app.py:67` — Source and pinned line verified
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/audit_policy_api.py:30` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/audit_policy_api.py:41` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/audit_writer.py:27` — Source and pinned line verified
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/audit_writer.py:45` — Source and pinned line verified
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/claims_api.py:24` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/claims_api.py:27` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/denial_events.py:18` — Source and pinned line verified
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/governance_g6_api.py:32` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/governance_g6_api.py:44` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/ingestion/review.py:19` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/intelligence_g8_api.py:54` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/intelligence_g8_api.py:69` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/login_limits.py:37` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/mfa_recovery.py:22` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/preflight_g9.py:118` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/preflight_g9.py:119` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/rate_limits.py:58` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference.py:72` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference.py:73` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference.py:74` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference_api.py:91` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference_api.py:94` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference_service.py:36` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference_service.py:60` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference_service.py:69` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference_service.py:81` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference_service.py:110` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference_service.py:126` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference_service.py:146` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reference_service.py:167` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/reporting_g7_api.py:49` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/retention.py:21` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/retention.py:36` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/retention.py:37` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/retention.py:40` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/retention.py:41` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/retention.py:51` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/retention.py:52` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:mcias/seed/loader.py:30` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:scripts/benchmark_operational_indexes.py:42` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:scripts/check_integrated_workflow.py:80` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:scripts/check_integrated_workflow.py:172` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:scripts/check_integrated_workflow.py:206` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:scripts/check_retention_browser.py:80` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `65bbddc1ae95aed22e157774f600a296a6e43926:scripts/retention_worker.py:23` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:scripts/retention_worker.py:24` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:scripts/retention_worker.py:25` — Audit identifier reference needs call path inspection
- `65bbddc1ae95aed22e157774f600a296a6e43926:tests/test_g9_postgres.py:46` — Artifact source line does not match pinned git file
- `65bbddc1ae95aed22e157774f600a296a6e43926:tests/test_l2_denial_transaction_regression.py:53` — Artifact source line does not match pinned git file
- `65bbddc1ae95aed22e157774f600a296a6e43926:tests/test_l2_denial_transaction_regression.py:71` — Artifact source line does not match pinned git file
- `65bbddc1ae95aed22e157774f600a296a6e43926:tests/test_postgres_integration.py:49` — Artifact source line does not match pinned git file
- `65bbddc1ae95aed22e157774f600a296a6e43926:tests/test_postgres_integration.py:51` — Artifact source line does not match pinned git file
- `65bbddc1ae95aed22e157774f600a296a6e43926:tests/test_postgres_integration.py:64` — Artifact source line does not match pinned git file
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/audit_policy_api.py:30` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/audit_policy_api.py:41` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/audit_writer.py:19` — Source and pinned line verified
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/audit_writer.py:34` — Source and pinned line verified
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/claims_api.py:24` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/claims_api.py:27` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/governance_g6_api.py:32` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/governance_g6_api.py:44` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/ingestion/review.py:19` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/intelligence_g8_api.py:54` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/intelligence_g8_api.py:69` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/login_limits.py:37` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/mfa_recovery.py:22` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/preflight_g9.py:118` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/preflight_g9.py:119` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/rate_limits.py:58` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference.py:72` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference.py:73` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference.py:74` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference_api.py:91` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference_api.py:94` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference_service.py:36` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference_service.py:60` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference_service.py:69` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference_service.py:81` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference_service.py:110` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference_service.py:126` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference_service.py:146` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reference_service.py:167` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/reporting_g7_api.py:49` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/retention.py:21` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/retention.py:36` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/retention.py:37` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/retention.py:40` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/retention.py:41` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/retention.py:51` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/retention.py:52` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:mcias/seed/loader.py:30` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:scripts/benchmark_operational_indexes.py:42` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:scripts/check_integrated_workflow.py:80` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:scripts/check_integrated_workflow.py:172` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:scripts/check_integrated_workflow.py:206` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:scripts/check_retention_browser.py:80` — Commit/rollback present, but audit relation cannot be established/ruled out from current function
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:scripts/retention_worker.py:23` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:scripts/retention_worker.py:24` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:scripts/retention_worker.py:25` — Audit identifier reference needs call path inspection
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:tests/test_g9_postgres.py:46` — Artifact source line does not match pinned git file
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:tests/test_postgres_integration.py:49` — Artifact source line does not match pinned git file
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:tests/test_postgres_integration.py:51` — Artifact source line does not match pinned git file
- `f9a0d126f33e8749e333166a2fc6c8d3a176dfc1:tests/test_postgres_integration.py:64` — Artifact source line does not match pinned git file
