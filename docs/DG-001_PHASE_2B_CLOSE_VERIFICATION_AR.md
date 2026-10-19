# DG-001 — Phase 2B-CLOSE consumer verification evidence and HANDOFF
Status: AUTOMATED FILE COVERAGE VERIFIED; SEMANTIC COVERAGE REVIEW OPEN. Not operationally accepted.
Date: 2026-10-20.
Run: https://github.com/overurdream-collab/test2/actions/runs/39330289038
Run input code SHA: 69ae380153536371791f2fd41f453e3eff68fe31
Artifact: shared-audit-consumer-inventory, artifact ID 12224321555, sha256 digest 12891f2fa22bab9515aefd7f1119ea409442abe5560a5c22e92708983906bf6c.
Reproducible script: scripts/audit_consumer_inventory.py
Workflow: .github/workflows/shared-audit-consumer-inventory.yml

## SHA-pinned actual execution evidence
| Reference | SHA | Python files | Read/parse OK | Errors | Matches | Positive files |
|---|---|---:|---:|---:|---:|---:|
| main | b69defa2f621458ef44d790b510840307a81009a | 206 | 206 | 0 | 255 | 70 |
| PR25 | a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1 | 215 | 215 | 0 | 323 | 75 |
| PR28 | 65bbddc1ae95aed22e157774f600a296a6e43926 | 213 | 213 | 0 | 292 | 78 |
| PR29 baseline | f9a0d126f33e8749e333166a2fc6c8d3a176dfc1 | 210 | 210 | 0 | 300 | 73 |
| TOTAL, including repeated cross-ref files | | 844 | 844 | 0 | 1170 | 296 |

Files.csv contains every scanned Python file even zero matches; matches.csv includes nearest function, line, source, SHA and kind; summary.json counts all failures. CI completed SUCCESS with no failures. Other SQL, dynamic Python/SQLAlchemy usages and wrappers still require semantic tracing. A token match is NOT a validated event or transaction chain. The code intentionally pins PR29 to the last design baseline so this documentation/scan-only change does not shift coverage during execution; inspect subsequent additions separately.

## Confirmed semantic paths (manual review)
| Ref | File / function | Event | Current business owner / audit owner | Contract conflict / required change |
|---|---|---|---|---|
| main | mcias/auth.py authenticate | login | auth session / local commit | preserve atomic session success; writer not yet used |
| main | mcias/auth.py require_permission | permission_denied | guard / guard commit | P0 rejected business changes may be committed; change to typed exception and HTTP owner |
| main | mcias/auth.py revoke_session | logout | auth / local commit | convert with same business transaction |
| main | mcias/tenant.py require_organization | tenant_access_denied | guard / guard commit | P0 move event after HTTP rollback |
| main | mcias/governance.py deny | governance_denied | governance / guard commit | P0 commit before 403, must be eliminated in future integration |
| main | mcias/governance.py activate_rule | rule_activated | governance / governance commit | retain success event transaction atomicity |
| main | mcias/reference_service.py _audit | contract_draft_created, tariff_added, beneficiary_category_created, beneficiary_enrolled | reference business / business commit | direct AuditLog; details e.g provider_code, contract_id, category_id omitted by strict 2A; no free-text expansion |
| PR25 | mcias/reference_service.py create/revise | contract_draft_created, contract_draft_revised | reference business / write_event | review action/resource/opaque IDs; metadata mapping |
| PR25 | mcias/reference_api.py create_contract / revise_contract | contract_creation_denied, contract_revision_denied | HTTP endpoint / local independent writer | duplicate 403 potential if PR28 owner also writes; 409 separate |
| PR25 | mcias/workspace_api.py activity_history | activity_read_denied | endpoint / local commit | same duplicate and rejected transaction risks |
| PR28 | mcias/app.py get_db and denial_events.py record_denial_after_rollback | authorization 403 | request session rollback / HTTP request owner independent writer | source-of-truth for L2; no PR28 integration in main |
| PR29 | mcias/audit_writer.py write_event, record_outcome_independent | success / denied / error | caller transaction / dedicated independent transaction | public signatures preserved; validates all fields, no durable request-id |
| PR29 | mcias/audit_contract.py new_request_attempt_id | request attempt UUID | generator only | not installed middleware, not persisted, no dedup |

## Follow-up semantic checks remaining
1. Filter the 1170 rows by constructor and audit wrappers, inspect every positive file and trace all relevant functions to FastAPI routers / calling services.
2. Resolve nested helpers, dynamic getattr/imports, ORM event handlers, raw SQL issued through text()/exec_driver_sql, and audit records written by jobs outside HTTP.
3. Verify exact transaction boundaries and whether exceptions escape dependency cleanup; ensure no 403 multi-owner path is mislabeled as a proven duplicate in existing separate branches.
4. Confirm allowed event registry, compatibility of every source action/resource_id, especially IDs that may carry sensitive identifiers.
5. Business conflict 409 canonical outcome is pending decision (separate event class vs fourth outcome).
6. UNKNOWN requires durable event identity and journal/queue selection plus true PostgreSQL lost-ack recovery tests. Neither implemented.
7. Re-run and examine full source inventory before accepting integration; current evidence is exhaustive read/parse coverage for pinned Python refs, not exhaustive semantic validation.

## DG-001 Worklog / handoff
The snapshot verified all 844 tracked Python files on the four referenced SHAs, with zero unreadable/parse-failed files. No production, database or migration tests executed here. Scope limited to scripts, CI and docs in PR29. Keep main, PR25, PR28, audit_writer.py, models.py and Alembic unmodified.
Acceptance requested: PARTIAL — AUTOMATED INVENTORY PASS, SEMANTIC INVENTORY NOT YET CLOSED. Do not merge, deploy or begin Phase 3.
