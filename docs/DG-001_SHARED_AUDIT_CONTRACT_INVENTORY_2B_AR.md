# DG-001 — Shared Audit Writer: contract finalization and consumer inventory
Status: DESIGN ONLY, NOT operationally accepted. Review baselines (2026-10-20):
- main b69defa2f621458ef44d790b510840307a81009a
- PR25 a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1
- PR28 65bbddc1ae95aed22e157774f600a296a6e43926
- PR29 113df4b9c2a451f4caa4ee082ac5b45f12b4642d
- L1 fix 9c5a578c23e79f7176ea5c924a2a431ac7a01aeb

## Reproducible complete inventory — required independent gate
Execute the following READ-ONLY script on separate clean checkouts of each pinned SHA. Scan every Python file, including tests and scripts, not only mcias/. Export CSV to review. Inspect discovered helper functions and imported audit abstractions manually.

```python
import ast, csv, pathlib, re, subprocess
patterns = re.compile(r"AuditLog|write_event|record_outcome_independent|audit_log|commit\s*\(|rollback\s*\(", re.I)
sha = subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip()
rows = []
for path in sorted(pathlib.Path(".").rglob("*.py")):
    if ".git" in path.parts or ".venv" in path.parts: continue
    text = path.read_text(encoding="utf-8")
    try: tree = ast.parse(text)
    except SyntaxError: tree = None
    for i, line in enumerate(text.splitlines(), 1):
        if not patterns.search(line): continue
        owner = "<module>"
        if tree:
            defs = [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.lineno <= i <= getattr(n,"end_lineno",n.lineno)]
            if defs: owner = min(defs,key=lambda n:n.end_lineno-n.lineno).name
        rows.append([sha,str(path),owner,i,line.strip()])
with open("audit_inventory.csv","w",newline="",encoding="utf-8") as f:
    writer=csv.writer(f);writer.writerow(["sha","file","function","line","expression"]);writer.writerows(rows)
print("sha",sha,"matches",len(rows))
```

Follow-up: trace audit constructors, wrappers, direct SQL, SQLAlchemy Session.add()/commit()/rollback(), exception ownership, event name, actor/tenant provenance and cross-branch conflicts. Do not claim this automated regex alone proves complete semantic coverage. Check all scripts, tests, .sql files and migrations separately. No consumer integration is authorized.

## Verified consumer matrix — source-specific
| Branch / file:function | Current event | Owner now | Phase2A conflict / required future change |
|---|---|---|---|
| main auth.py:authenticate | login | auth commit | same transaction as session |
| main auth.py:require_permission | permission_denied | auth guard commit | P0 denied business mutation could commit; HTTP owner only |
| main auth.py:revoke_session | logout | auth commit | atomic revocation+event |
| main tenant.py:require_organization | tenant_access_denied | tenant guard commit | P0 change to raise metadata without commit |
| main governance.py:deny | governance_denied | governance guard commit | P0 owner rollback before audit |
| main governance.py:activate_rule | rule_activated | governance commit | preserve atomic success |
| main reference_service.py:_audit | contract_draft_created,tariff_added,beneficiary_category_created,beneficiary_enrolled and other reference operations | business service commit | direct AuditLog; unknown details stripped by 2A, audit owner contract review |
| PR25 reference_service.py: revise/create | contract_draft_created,contract_draft_revised | service | write_event used; typed metadata and source provenance review |
| PR25 reference_api.py:create_contract / revise_contract | contract_creation_denied,contract_revision_denied | endpoint independent commit | duplicate risk when PR28 HTTP owner integrated |
| PR25 workspace_api.py:activity_history | activity_read_denied | endpoint commit | duplicate risk and guard commits |
| PR28 denial_events.py:record_denial_after_rollback | tenant_access_denied or permission_denied | HTTP get_db post-rollback | correct ownership model, writer 2A validation |
| PR28 app.py:get_db | AuthorizationDenied | request owner | rollback then one independent writer call |
| PR29 audit_writer.py | success / denied / error | caller or independent session | public signatures preserved; finite validation but no persistence idempotency |

This is the confirmed matrix; completion is BLOCKED until the reproducible source inventory actually runs on each SHA.

## Closed event vocabulary — proposed, not deployed
| Canonical action | Allowed resources | Legacy aliases / source | Outcome | Permitted metadata |
|---|---|---|---|---|
| login | auth | login | success | none |
| logout | auth | logout | success | none |
| authorization_denied | permission,organization,rule,contract_version,audit_log | permission_denied,tenant_access_denied,governance_denied,activity_read_denied,contract_creation_denied,contract_revision_denied | denied | reason_code (closed enum) |
| rule_activated | rule | rule_activated | success | approved authorization opaque ID only after classified |
| contract_draft_created | contract_version | same | success | version,status |
| contract_draft_revised | contract_version | same | success | version,previous_version,previous_id,new_id |
| tariff_added | provider_tariff | same | success | no patient values or amounts |
| beneficiary_category_created | beneficiary_category | same | success | none |
| beneficiary_enrolled | beneficiary_enrollment | same | success | no beneficiary token |
| business_conflict | contract_version,provider_tariff,rule | reference_conflict / HTTP409 handler (proposed) | conflict (requires contract decision) | reason_code |
| operation_failed | auth,contract_version,rule,organization | proposed | error | reason_code |

Legacy rows remain untouched; reader maps legacy name to canonical projection, never overwrites history. Event/resource validation MUST be registered pairs, not regex alone. Values passed into action, resource_type, resource_id must originate from server-controlled enums / opaque identifiers and typed allowlists. Do not store contract_number, patient/family identity, diagnoses, prescriptions, free text, credentials, access tokens or exception SQL.

## Transaction owner agreement
SUCCESS: add to business Session, then owner commits once; audit failure aborts business commit.
403 DENIED: guard raises typed denial without db.commit; HTTP transaction owner rolls back first; one independent audit write. Endpoint and owner cannot both persist.
409 CONFLICT: distinguish actual business conflict from authorization denial and maintain separate taxonomy.
5xx ERROR: rollback; retain original exception for diagnostics; safe secondary event with explicit failure propagation and no secrets.
AUDIT FAILURE: never silently swallow; preserve original exception via cause/chained incident record, communicate audit unknown/failure to operators without leaking PHI.

## Request attempt & dedup (FUTURE)
Generate request_attempt_id UUIDv4 from trusted server ingress for *each received HTTP request*, independent of client Idempotency-Key; propagate via request-scoped context. Distinct HTTP retries have distinct attempt IDs. One centralized authorization_denied event_type per request; deferred partial UNIQUE index on (request_attempt_id,action) WHERE attempt_id IS NOT NULL AND action='authorization_denied' (PG partial UNIQUE is immediate, not deferred). Other multi-event actions need distinct event-subtype key. Never rely on Python process memory or select-then-insert. No persistence exists yet, hence no exactly-once guarantee.

## UNKNOWN commit outcome
Use existing AuditLog.id as stable event_id: allocate before save and retain in durable *separate* journal / trusted queue BEFORE any risky commit; journal must not contain PHI. States COMMITTED (positive receipt or verified event row), ROLLED_BACK (authoritative failed transaction), UNKNOWN (commit response lost or ambiguous). On restart, reconcile outstanding events by event_id in correct tenant/database through new trusted connection; no new event_id; absence in one read is insufficient to prove rollback. Re-insert is prohibited until protocol formally proves it safe. Operate alerting by event_id/status only. Actual PG16 tests: deferred-trigger commit rejection, connection kill before COMMIT, kill/drop TCP during COMMIT, commit success+lost ACK, retry concurrency, restart journal reconciliation. No UNKNOWN real-failure claim now.

## AuditLog future schema
Current columns id (String36 primary key = event_id), actor_id(nullable), action (=event_type), resource_type, resource_id(String36 nullable), details(JSON), created_at. Historic details may have organization_id/outcome but not uniformly.
Add nullable request_attempt_id(UUID), operation_id(UUID), organization_id(same FK type as organizations.id, String36), outcome(varchar with CHECK after closed enum is approved). Index (organization_id,created_at,id); (request_attempt_id); (operation_id). Partial unique (request_attempt_id,action) for single-denial event after canonicalization. Historic rows remain NULL, immutable trigger remains active. No backfill changing history; verified reader projection with trusted actor/tenant policy. Expand/compat/contract migrations only after L1 Alembic target gate independently accepted and approved synthetic PG16 migration/downgrade strategy. No Alembic file written here.

## Anonymous events — DISABLED
Never fake actor/tenant. Only future approved security provenance may use actor_id=NULL, organization_id=NULL when unknown. Allow approved login failure / invalid session / rate-limit event codes only; retain only bounded nonreversible identifiers after explicit privacy analysis. Distinct security.audit.read role, no tenant reader access to anonymous security events; no raw tokens, passwords, patient info. Retention period/export destination/pseudonymization and legal hold require explicit supervisor approval; no enabled writer path now.

## P0/P1 and acceptance
P0 main guard commits, duplicate 403 with PR25, unsolved lost-ACK UNKNOWN, no database uniqueness, unchecked true semantic consumer inventory.
P1 detail loss with typed contract, historic reader tenant behavior, anonymous retention pending, new canonical outcome conflict enum not accepted.
Next scoped implementation only with separate approval; first complete full checkout inventory and approve event registry+conflict outcome semantics; then L1-gated migration, HTTP owner integration, real PG fault/concurrency test, Shared Audit/L1/L2/G1-G9/Enterprise gates.

## DG-001 HANDOFF
Docs-only addition on PR29. Keep audit_writer.py, models.py, all Alembic, app/auth/tenant/reference services untouched. No PR25/28/main modifications. No operational acceptance. Verify new final PR head, document checks and generated matrix before accepting consumer inventory as COMPLETE.
