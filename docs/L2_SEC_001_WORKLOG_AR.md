# L2-SEC-001 — DG-001 Worklog
Date: 2026-10-18
Base main: b69defa2f621458ef44d790b510840307a81009a
Branch: fix/mcias-l2-denial-transaction-safety

## Baseline / evidence
Previous SQLite synthetic reproduction: FAIL for both denied guards; independent-transaction denial writer pattern: PASS. These were not PostgreSQL or original-function runs.
Existing L2 evidence retained outside this branch; do not rewrite historical failures.

## Decisions
The shared audit writer exists in draft PR #25, not in main. Do not duplicate it, cherry-pick another owner's work, or claim it is available to this branch. Integration remains BLOCKED.
A new isolated PostgreSQL regression test uses original guard functions and refuses non-local or non-_l2_e2e targets. It performs no migrations.
Before any final approval, implement the FastAPI request transaction-owner rollback and one denial audit event via PR #25's shared writer, with an event de-duplication contract.

## Current status
PARTIAL / BLOCKED. No safe PostgreSQL target verified. No final PASS. No merge or deploy.


## 2026-10-18 — Corrected regression
Commit 23be2dad4eae611a4a6b7c76ee455a866751183b: test checks independent session BEFORE rollback; uses only disposable L2-SYNTHETIC fixture; restores leaked baseline mutation after observation; absence of safe PostgreSQL is explicit FAIL/BLOCKED, not a skip/PASS. Original guard implementation remains unchanged, so expected original result on PostgreSQL is FAIL, but unexecuted. No PostgreSQL local tool/service confirmed. Shared writer remains only on PR #25. Do not claim completion.

## 2026-10-19 — PostgreSQL 16 RED proof and partial fix
Baseline RED: GitHub Actions run 39257009551 on SHA 7315b8f9f323737cbf9ac5da7721dfe042a037c0: two tests failed with 'original guard committed pending business update'; PostgreSQL 16.15 isolated service, migration and synthetic fixture completed. Historical RED log: https://github.com/overurdream-collab/test2/actions/runs/39257009551 .
Added dedicated L2 PostgreSQL workflow; standard unit suite does not require PostgreSQL and skips L2-only test outside dedicated gate (skip cannot constitute final security PASS).
Updated auth.py, tenant.py to emit AuthorizationDenied without commit, app.py get_db exception owner to rollback, denial_events.py delegates to PR #25 writer via lazy import. Writer absent in main: real integration BLOCKED. No copied writer, no modifications to PR #25. Runtime denial event recording without dependency raises, preventing false audit-success claims. Final integration, compatibility tests and Green CI pending.

2026-10-19 owner contract: added tests/test_l2_request_owner_contract.py to invoke actual get_db generator and original guards, then verify rollback before exactly one spy sink call and independent-session business state. Spy is NOT PR #25 real writer; durable audit and real HTTP integration remain BLOCKED. Legacy tests/test_tenant_isolation.py is unchanged, still asserts two persisted rejection events on direct guard invocation, which is incompatible with the new request-owner contract. Do not delete or weaken its assertions merely to obtain green CI; propose a separately reviewed replacement with equal or stronger durable-event coverage once actual shared writer is available. Previous PostgreSQL RED 39257009551 and guard GREEN 39257480016 retained. 

2026-10-19 REAL WRITER INTEGRATION: PR25 commit 60f1db7d174e9d1a29921ed578392ed5705b2874, writer blob 509ce4124f012cc4a121294fe9122c9384902fd6. Temporary GitHub Actions composition via git show into disposable runner, no PR25 or main modification and no source copy committed to PR27. Real HTTP + PostgreSQL 16 request rollback and exactly one durable denial event PASS: https://github.com/overurdream-collab/test2/actions/runs/39268867485 on SHA f461a99e1bc365c3c79eaddae7bc70fbd9579017. Added cross-tenant negative assertions requiring recheck on final SHA. Contract: guard constructs event metadata; FastAPI get_db rollbacks business; record_denial_after_rollback invokes real PR25 record_outcome_independent with SQLAlchemy bind, actor_id, organization_id, action, resource_type, resource_id, outcome=denied and filtered reason_code. Writer opens independent Session, reloads actor, enforces same tenant and active, commits once or raises. Runtime main still lacks writer and original test_tenant_isolation asserts immediate audit rows from direct guard call, so production/merge BLOCKED. No replay idempotency key in current writer; one event per single HTTP attempt verified, not retry-dedup. Original PostgreSQL RED remains run 39257009551. No merging, deployment or PHI.


## 2026-10-19 — Supervisor permission controls review
Three required checks for any edit operation:
(1) UI: authenticated viewer without the operation's write permission must not see an Edit control; reviewed PR25 mcias/web_workspace/app.js blob a8fe335c84c42e425b944b78242197ace87e0b5a. It gates restricted routes on context.permissions, but no edit/revise/Edit/تعديل control found in that file. Thus button-level negative visibility is NOT VERIFIED, not PASS. Do not infer global absence from one UI file.
(2) Server: PR25 mcias/reference_api.py revise_contract calls _actor(db, authorization, "reference.write"); _actor invokes require_organization, enforcing server-side RBAC. Source-level guard CONFIRMED; direct unauthorized actual revise endpoint on composed code still needs HTTP test, so end-to-end remains unverified.
(3) Transaction+audit: L2 PostgreSQL isolated run 39257480016 and latest 39269230524 show original guards do not commit pending business writes. PR25 real writer temporary composition run 39269230517 shows one tenant-scoped durable denial after request-owned rollback for synthetic HTTP probe; this is NOT the actual production revise endpoint and doesn't establish retry idempotency.
Required future focused tests when edit UI is located: run authorized/unauthorized browser DOM assertions on the real Edit component; direct POST revise as read-only user must return 403, no row/version changes or financial mutation; independent-session audit row exact one with trusted tenant, no PHI; verify cross-tenant denied. Preserve all legacy tests.
No UI redesign or RBAC changes made.

2026-10-19 L2 continuation: checked PR25 real audit writer blob 509ce4124f012cc4a121294fe9122c9384902fd6. Requested owner contract decision in PR25 comment 6274185977 (https://github.com/overurdream-collab/test2/pull/25): duplicates in contract creation, anonymous identities and retry correlation. Enhanced disposable PostgreSQL real-writer integration test: two distinct forbidden HTTP requests (tenant and sensitive medical field), each must rollback changes and add exactly one independently readable same-tenant AuditLog; negative cross-tenant writing remains tested. Existing test_tenant_isolation.py untouched; old direct-guard expectation still unresolved due to ownership shift. No shared implementation copied into PR27, no branch merge or deployment. Await new CI evidence and PR25 owner decision; L2 remains BLOCKED.

2026-10-19: CI evidence run 39301920897 real shared writer HTTP/PG16 PASS for two distinct 403 requests with one durable same-tenant denial each and rollback (temporary real PR25 writer). Run 39301920825 L2 PostgreSQL gate PASS, run 39301920947 G9 PASS. G1-G7 run 39301920919 failed because new integration test read PG env vars at module import (collection KeyError), not a transaction failure; corrected by deferring env access to test invocation, general suite skips when not provisioned, dedicated acceptance job sets MCIAS_L2_AUDIT_REQUIRED=YES and fails closed if DB absent. PR25 coordination comment https://github.com/overurdream-collab/test2/pull/25#issuecomment-6274185977 . The older tenant isolation test remains unchanged and its audit persistence coverage unresolved. No merge, PR25 modification, writer copy or deploy. Final CI pending on corrected commit.
