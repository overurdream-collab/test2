# MCIAS v2.0 — Shared Audit Writer Ownership & Compatibility Resolution (DG-001)

**Decision:** READ-ONLY COMPARISON & MINIMAL COMPATIBILITY PROPOSAL ONLY. **Status:** DESIGN PROPOSAL / OWNER APPROVAL REQUIRED / NO MERGE OR DEPLOYMENT.  
**Review date:** 2026-10-21. **Writing scope:** documentation on PR #29 only.

## 1. Verified heads and provenance
| Reference | Verified HEAD | Branch | State |
|---|---|---|---|
| [PR #25](https://github.com/overurdream-collab/test2/pull/25) | `8a616f7f68f506df08deccd62a9faa7d7ec89272` | `feat/mcias-input-triactions-e2e` | Draft; base is `feat/mcias-temporal-inputs-triage-ui`, NOT main |
| [PR #29](https://github.com/overurdream-collab/test2/pull/29) | `fd1bb1d22f1957f40688baa207cdf449b0690cd9` | `feat/mcias-shared-audit-writer-phase1` | Draft; base main |
| [PR #31](https://github.com/overurdream-collab/test2/pull/31) | `f9f4038bacbd09e92df4a67aff1c0a633e409dfa` | `feat/mcias-cai01-claims-batch-preflight` | Draft; base main |

Actual GitHub file blobs: PR25 writer `509ce4124f012cc4a121294fe9122c9384902fd6` (63 lines); PR29 writer `e17f58b06d191b28f9eaff340feeff0691c80edf` (52 lines); PR29 audit contract `88af554c6402679a2b87aa37b1268876c3507fde`. PR31 contains **neither `mcias/audit_writer.py` nor `mcias/audit_contract.py`**. They must not be assumed available in its checkout.

## 2. Complete line-difference register — writer 25 vs 29
A line-by-line longest-common-subsequence comparison of the complete original source identified **3 inserted PR29 lines and 14 removed PR25 lines**. Every unlisted writer line matches in the same order; there are **no changed function signatures and no changed flush/commit sequence**.

| Original PR25 line(s) | PR29 line(s) | Specific semantic change | Risk / decision |
|---|---|---|---|
| imports 7–8 | imports 7–9 | Added `from mcias.audit_contract import validate_event, clean_details` at 29:9 | PR29 requires atomic availability of `audit_contract.py`; using only writer module fails import |
| `_safe_details` body 16–25 | 29:17 | Replaced any allowlisted scalar `str/int/bool` up to 150 chars with typed `clean_details(details)` | Legitimate metadata may silently disappear; no legacy free-text fallback |
| writer checks 33–36 | 29:25 | Replaced outcome membership and action/resource **length checks** with `validate_event(action,resource_type,resource_id,outcome)` | Rejects invalid action/resource strings and free-text resource IDs; outcome set unchanged |
| all other lines | same function bodies | Actor/tenant validation, `AuditLog` construction, `db.add();db.flush()`, return record; independent `Session(bind)` -> `independent.get(User)` -> writer -> `commit()` -> event ID | No behavior regression evident in transaction code; actual composed PG16 test still mandatory |
| PR29 lines 11–13 | same as PR25 constant block | `_ALLOWED` and `_MAX` remain declared in PR29 but are no longer used by `_safe_details` | Stale constants, not an alternate acceptance policy; avoid editing during this review |

**Signatures preserved**:
- `write_event(db, *, actor, organization_id, action, resource_type, resource_id, outcome, details=None)`
- `record_outcome_independent(bind, *, actor_id, organization_id, action, resource_type, resource_id, outcome, details=None)`

**Business transaction:** `write_event` rejects inactive/mismatched actor, stages AuditLog in caller session, calls `db.flush()` and returns ORM event. Caller alone owns `commit()` / `rollback()`; `flush()` is NOT proof of durable event.  
**Independent denial/error:** caller must rollback business session first. `record_outcome_independent` creates fresh SQLAlchemy Session, refetches actor, reuses `write_event`, commits and returns ID. Exceptions propagate; a failed commit or lost acknowledgement is not a proven durable record. Context closes/rolls back pending uncommitted transaction on failure. Neither writer has a durable request attempt ID, deduplication constraint, or proven UNKNOWN settlement.

## 3. Exact PR29 contract and compatibility
`audit_contract.py`:
- `action`: ASCII `^[a-z][a-z0-9_]{0,119}$`, `resource_type`: ASCII `^[a-z][a-z0-9_]{0,89}$`; these are **syntax restrictions, NOT an event/resource pair registry**.
- `resource_id`: NULL or opaque ASCII `^[A-Za-z0-9][A-Za-z0-9_.:-]{0,35}$`. A syntactically valid identifier is not proof of tenant ownership or absence of PHI.
- `outcome`: exactly `success`, `denied`, `error`; no approved `business_conflict` outcome.
- `details`: allowlisted typed `version/previous_version` nonnegative bounded integer (bool rejected), `previous_id/new_id` opaque identifier, `effective_from/effective_until` real ISO date, `reason_code` restricted enum, `status` restricted enum. `contract_number` is listed but **always dropped**. Unknown keys dropped silently, not persisted or error-reported.
- `new_request_attempt_id()` creates UUID4 per call but does NOT install request middleware or persist IDs. No exactly-once claim.

**Compatibility decision:** retain PR29 as security baseline and **do not restore PR25 scalar-any metadata behavior**. Require an explicit per-consumer typed mapping. For mandatory correlation data, silent stripping must be caught in a synthetic integration assertion and resolved by owner-approved safe linked resource / typed data contract; never broaden `details` merely to pass legacy tests.

## 4. Consumer and test matrix (not branches merged)
| Branch, source and lines | Calls / observed event | Transaction owner | PR29 compatibility | Evidence/tests |
|---|---|---|---|---|
| PR25 `mcias/reference_service.py:46–50` | `write_event` `contract_draft_created`, `contract_version`, version and contract_number | `create_draft` commits success in same session | action/resource/UUID format valid; `version` survives, **contract_number silently omitted** | `scripts/check_contracts_acceptance.py:233–249`, strict Chromium+FastAPI+PG16 |
| PR25 `mcias/reference_service.py:81–86` | `write_event` `contract_draft_revised`; previous_id, previous_version, version, contract_number | `revise_contract_draft` same session | prior opaque IDs and integer versions survive; **contract_number omitted** | acceptance script 288–318 asserts event and previous_id |
| PR25 `mcias/reference_api.py:100–126` | `record_outcome_independent` `contract_creation_denied` for 403 AND 409 | endpoint rolls back and independently commits | `reason_code` permission_denied/reference_conflict allowed; **409 misclassified denied**; risk of duplicate 403 on later L2 composition | strict acceptance 240–247 currently expects denied 409 |
| PR25 `mcias/reference_api.py:228–247` | `record_outcome_independent` `contract_revision_denied` on conflict | endpoint rollback then independent commit | `revision_rejected` accepted; caller's _actor happens before local try, so 403 from guard is different audit path; distinguish 409 | acceptance 309–318 |
| PR25 `mcias/reference_service.py:10–12,109,118,129,158,173,193,215` | **direct** `AuditLog` via `_audit` for tariff/category/enroll/approval/import | reference service itself commits | bypasses PR29 validation; legacy `contract_id,category_id,provider_code` etc not in PR29 typed details | require future contract inventory regression; not all consumers converted |
| PR25 `mcias/workspace_api.py:108–136` | direct AuditLog activity_read_denied then `db.commit()` before 403; reads audit rows | endpoint | bypasses independent writer, may commit pending business writes; later duplicate L2 risk | strict activity/role tests; no 403 ownership guarantee |
| PR29 `mcias/audit_writer.py` | writer's own two public functions, no G3/G5 consumers copied from PR25 | caller success / dedicated independent session | baseline under test, not itself evidence integration | `tests/test_shared_audit_writer_phase1_pg.py` six real PG16 tests; `tests/test_shared_audit_phase2a_contract.py` privacy/ID/signature tests; dedicated workflow |
| PR31 `mcias/audit_service.py:22–85` | `run_audit` builds AuditSnapshot, flushes, **directly** creates `AuditLog(action='audit_snapshot_created', resource_type='audit_snapshot', resource_id=snapshot.id)` then commits | `run_audit` commits business + direct audit | **NO call to PR29 writer; bypasses Phase2A sanitization;** free-form direct `details` claim_id, policy_fingerprint, verification_status. `resource_id` is promising stable snapshot reference | CAI-01 preflight does not prove shared-writer composition |
| PR31 `mcias/claims_batch_preflight.py` | source-scope diagnostic; no AuditLog writer | read-only function | NOT an audit consumer | `tests/test_cai01_batch_preflight.py`, `tests/test_cai01_inputs_first_source_contract.py` only |
| PR31 `docs/CAI01_SHARED_AUDIT_INTEGRATION_GATE_AR.md` | declares G2/G3/G4/G5->Shared Audit/Human Review requirement | no runtime | all twelve CAI-01 E2E scenarios documented blocked/not executed | document itself |

**Test evidence:** latest PR25 SHA `8a616f...` workflows G1–G7 `39466865992`, G8 `39466865707`, G9 `39466865945`, Enterprise `39466865861`, strict Contracts `39466866144`: all SUCCESS at that SHA. PR29 `fd1bb...` isolated Shared Audit PG16 `39335953135` SUCCESS, G1–G7 `39335953144` SUCCESS. PR31 `f9f403...` latest G1–G7 run `39511759535` overall FAILURE: unit and postgres-integration SUCCESS, **dependency-audit FAILURE**. These are different branches and distinct test scopes; zero evidence of CAI-01 full composed PG16 acceptance. Never reinterpret PR25 current 409-denial assertions as acceptance of the intended 403/409 taxonomy.

## 5. Proposed final contract — smallest compatible composition
1. **Authoritative code owner:** Shared Audit owner on PR29 exclusively owns `mcias/audit_writer.py` and `mcias/audit_contract.py`, future event registry, persistent identity/dedup and approved migrations. PR25 does **not** overwrite/shared-edit those files at integration; original writer blob must be retained as provenance only. No changes authorized by this document.
2. **PR25 owner's responsibilities:** keep and test G3/inputs `reference_service.py`, `reference_api.py`, `input_clause_service.py`, `workspace_api.py` and strict contracts harness. Identify all event names and required metadata; supply typed, trustworthy safe data / stable IDs; approve changed behavior for `contract_number` omission and 409; preserve existing G3 creation/revision and reader behavior; coordinate PR28 HTTP transaction owner so only one actor saves a 403. Do not create another writer or weaken privacy.
3. **CAI-01/PR31 owner's responsibilities:** provide G2 source row SHA/sheet/type/physical row manifest, G3 approved effective-dated reference IDs, G4 persisted claim link, G5 policy/rule/version/evidence link, and G6 human-review state; use shared writer only after Shared Audit owner authorizes API/representation. Do not claim PR31 currently imports writer or has runtime event-link coverage.
4. **Authorization/transaction contract:** SUCCESS uses `write_event` inside business Session prior to one caller commit; DENIED403 after business rollback is handled by **single request transaction owner** with independent writer; BUSINESS_CONFLICT409 separate approved taxonomy (not denied permission); ERROR5xx preserves original cause and safe audit failure reporting; never swallow AUDIT FAILURE. Current PR25 independent 403 calls and PR28 owner are not automatically composable.
5. **Correlation strategy proposed for minimal stage:** use `AuditLog(resource_type='audit_snapshot', resource_id=AuditSnapshot.id)` and trusted `AuditLog.details.organization_id/outcome`; the existing `AuditSnapshot` has FK `claim_id`, `organization_id`, `policy_id`, `policy_fingerprint`, calculation/findings/verification, while `ClaimEntry` has `extracted_record_id`. Follow chain AuditLog→AuditSnapshot→ClaimEntry→ExtractedSourceRecord→G2 source manifest, and snapshot policy→server-verified rule/reference/evidence ledger. **The last rule/reference/evidence link is NOT guaranteed by current schema** and must be verified or specified as owner-approved immutable reference, not inferred from arbitrary JSON. No untrusted raw data or PHI may be copied to AuditLog.
6. **If verified join is insufficient**, Shared Audit owner chooses minimal typed bounded correlation or durable join model under a new explicitly approved schema/migration scope after L1. Current allowlist may not be expanded under this review. Every mandatory field must either survive the approved persisted structure or cause integration to fail closed; no fabricated lineage and no hidden silent-drop acceptance.
7. Keep both writer function signatures. Every operational consumer must specify trusted actor/tenant, finite server-owned action/resource type, opaque tenant-proven resource ID, outcome, and validated typed metadata. Signed evidence and cross-tenant read policy are checked by responsible component owners. No per-request durable key, idempotency, UNKNOWN resolution or Exactly-once guarantee exists today.

## 6. Proposed **real PostgreSQL 16 synthetic compatibility test plan** (NOT executed)
**Environment:** only disposable named PG16 database with explicit synthetic allow flag; no production URL, existing audit migrations/append-only constraints; assemble **exact known PR25 G3 sources, PR29 writer+contract, CAI-01/G5 consumers** on a newly authorized isolated integration branch after owner agreement. Never blindly copy one writer onto another branch. Preserve separate baseline tests, no mocks or fabricated audit success.

| Test | Runtime action | Mandatory PostgreSQL proof / failure criteria |
|---|---|---|
| PG16-C01 signatures/imports | load writer and audit_contract from owner-approved composed tree, compare original signatures | no import failure; no silent fallback to PR25 sanitizer |
| PG16-C02 G3 create/revise | create synthetic org and active actor + G3 numbered draft, revise in separate transaction | exactly one success per operation; prior/new link, org, version survive; contract_number not exposed; source business mutation rolls back if audit flush fails |
| PG16-C03 403 and 409 | deny authorized vs unauthorized G3 action in real FastAPI transaction; force business conflict | 403 has single independent event AFTER rollback with no pending business mutation; 409 separately classified by approved taxonomy; current PR25 behavior must not be misrepresented |
| PG16-C04 CAI-01 source | synthetic XLSX includes CLAIMS row and PAYMENT row, verify approved sheet provenance and raw row accounting | one `ClaimEntry` from valid CLAIMS, PAYMENT retained/excluded; verify source SHA, sheet/row and G4 IDs in persisted trusted lineage |
| PG16-C05 actual G5 audit + shared writer | run real authorized G5 service on synthetic ClaimEntry with approved service-date G3 reference and check plan | one committed `AuditLog` event ID linked to `AuditSnapshot`, `ClaimEntry`, org, G3 reference version, G5 policy/rule version, evidence identifiers and human-review routing; each FK/JSON reference proven by SELECT after fresh session, not by Python in-memory values |
| PG16-C06 privacy/tenant | try patient name, diagnosis, Rx, raw token, arbitrary reason_code, cross-tenant ID and unauthorized reader | data absent from ALL fields/storage/logs; cross-tenant correlation not readable; mandatory missing correlation fails closed |
| PG16-C07 error/restart | force PG constraint violation at flush, deferred commit rejection, lost ACK/connection fault, and consumer restart | business+success atomic rollback; independent denial persistence or visible failure; UNKNOWN remains UNKNOWN until DB-confirmed resolution; no duplicate or Exactly-once claim |
| PG16-C08 human review | audit missing/incomplete/expired/valid dated reference and route via existing G6 | `HUMAN_REVIEW`/unresolved on insufficient evidence, no automatic approval/rejection/deduction; committed event links to human review ID when authorized |

**Cross-check:** preserve PR25 strict Chromium/PG16 assertions (plus approved new 409 taxonomy and metadata field behavior); PR29 privacy and PG16 unit/real DB assertions; PR31 CAI01 source preflight + twelve actual E2E scenarios when all owners unlock. Run affected G1–G7, G8, G9, Enterprise, L2, L1 safety and dependency-audit on **same integration SHA**, save case IDs, event IDs, row-level evidence and run links. Existing prior successful runs do not establish cross-branch composability or schema availability.

## 7. Risk / decision register
| ID | Severity/category | Evidence | Proposed limited remediation, not executed | Approval gate |
|---|---|---|---|---|
| AW-C01 | P0 FILE OWNERSHIP | PR25/PR29 same writer path, distinct blobs | PR29 only source of shared writer; PR25 owns G3 consumer adaptations; do not select one whole branch's file blindly | AI CTO + both owners acknowledge |
| AW-C02 | P0 COMPATIBILITY | PR25 legacy `contract_number` retained, PR29 drops; G5 claim/rule/evidence keys absent | approved typed/linked representation with regression assertion | Shared Audit + PR25 + CAI owner |
| AW-C03 | P0 BYPASS | PR25 `_audit` and PR31 G5 direct AuditLog constructors | later owner-scoped adoption; preserve all existing business services | Shared Audit + respective consumer owner |
| AW-C04 | P0 TRANSACTION | PR25 endpoint independent 403 and PR28 central L2 owner; 409 currently denied | choose single HTTP owner, distinct 409 event category after policy approval | L2 security + PR25 + Shared Audit |
| AW-C05 | P0 PROOF GAP | CAI01 gate: 12 cases blocked; none of claim/reference/rule/evidence/human review proven E2E | real synthetic PG16 composite, verify persisted graph | AI CTO authorizes isolated integration and all owners |
| AW-C06 | P1 PRIVACY | PR25 scalar allowlist permits business-origin fields; PR29 validates syntax but not finite action/resource pair registry | retain stricter contract, approve closed event pairs and typed provenance before operational use | security/privacy + Shared Audit |
| AW-C07 | P0 UNKNOWN/DEDUP | no durable request_attempt_id, no unique DB guard, no reconciliation | separate future schema + L1 safety + PG16 fault proof | new explicit implementation approval |
| AW-C08 | P1 CI SECURITY | PR31 current G1–G7 run 39511759535 dependency-audit FAILED (unit/PG job SUCCESS) | security dependency owner handles separately, no bypass | dependency security owner |

**Decision:** READY FOR INDEPENDENT OWNERSHIP/CONTRACT REVIEW, **NOT READY FOR INTEGRATION EXECUTION**. Approval requested only for file ownership, bounded compatibility representation, event/rule/ref linkage, 403/409 transaction ownership and future isolated test scope. No approval to edit source, perform migrations, merge, deploy, or decide finances.

## 8. DG-001 Worklog & HANDOFF
**Scope:** read-only comparison of exact latest HEADs and real code + test dependencies; one documentation-only deliverable added to PR29.  
**Verified:** writer complete LCS comparison, PR25 G3 callers/direct bypass, PR29 typed sanitizer and PG16/unit coverage, PR31 G5 direct AuditLog + CAI-01 integration blocker, same-SHA CI statuses.  
**NOT EXECUTED:** cross-branch import/composite integration, any new PG16 test or CAI real 12-scenario journey, schema change, deployment.  
**Handoff:** after formal AI CTO/shared owner+PR25+CAI/L2 agreement, apply only owner-scoped changes with explicit implementation authorization; verify HEAD/CI anew. Keep PR31 docs and all historically reported evidence unchanged. Do not run financial automation.
