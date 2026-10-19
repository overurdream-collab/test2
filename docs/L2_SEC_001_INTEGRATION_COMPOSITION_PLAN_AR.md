# MCIAS L2-SEC-001 — DG-001 Integration Composition Proposal
Date: 2026-10-19
Decision: PROPOSAL ONLY — independent integration branch NOT created; no merging/deployment.
Repo: overurdream-collab/test2
PR #25: feat/mcias-input-triactions-e2e (50 commits ahead of common main at inspection)
PR #27: fix/mcias-l2-denial-transaction-safety (44 commits ahead of common main at inspection)
Common ancestor main SHA: b69defa2f621458ef44d790b510840307a81009a
PR27 last documented SHA before plan: fdba902bb5ff97ba7f4a3cff3bdba13d023ff9ef
Note: branch heads must be re-fetched and pinned immediately BEFORE authorized composition, because both agents may update.
Sources: GitHub compare_commits for both branches and source inspection of mcias/app.py, audit_writer.py, reference_api.py.

## 1. Proposed composition base
Preferred independent branch name after explicit central approval:
integration/mcias-pr25-pr27-l2-audit
Create from freshly verified PR25 HEAD (PR25 is the superset providing audit_writer.py, contracts, migration versions 0019/0020 and related templates/tests), then merge PR27 HEAD ONLY into the temporary integration branch. Never merge main, never change either source branch. Resolve app.py overlap manually and document exact diffs; do not overwrite PR25 router additions or PR27 rollback handling. If provenance or merge conflicts cannot be safely resolved, stop and report BLOCKED; do not force a merge or copy a standalone writer.

## 2. Dependency graph
main common ancestor -> PR25 (shared audit writer, reference_api & reference_service, workflow, G3 editing, migrations 0019 and 0020)
main common ancestor -> PR27 (AuthorizationDenied guards, get_db request-owner rollback, denial_events adapter, mandatory PostgreSQL/HTTP regressions)
PR25 HEAD + PR27 HEAD -> isolated integration branch -> PostgreSQL16 synthetic migration -> HTTP/API/Enterprise/Contracts/G1-G9 acceptance.
PR25 writer blob observed: 509ce4124f012cc4a121294fe9122c9384902fd6. Re-verify if owner changes module.
Do not confuse temporary CI overlay PASS with buildable runtime dependency resolution.

## 3. Known conflicts and owners
- mcias/app.py modified in both branches: merge PR25 new input-clauses/audit-triage routers, cache controls and any middleware while keeping PR27 get_db rollback handler. Owner: joint L2 / PR25 reviewer; test route registration and import availability.
- mcias/reference_api.py PR25 owns contract creation/revision. Current create_contract() catches guard HTTPException and records contract_creation_denied; PR27 get_db also logs tenant_access_denied. A 403 attempt risks two logical security events unless owner/central supervisor chooses canonical ownership/taxonomy. DO NOT silently drop events. Proposed: exactly one canonical authorization-denial event per policy decision in request transaction owner; 409 business conflict remains one endpoint-domain event, not both.
- Audit writer rejects inactive, non-tenant or absent authenticated actor. Anonymous attempts need separately approved security-event contract; never fabricate actor/tenant.
- No committed idempotency/correlation key in PR25 writer; concurrent/retry logical de-dup is not proven. Exact-once-per-request currently verified only in bounded tests; choose correlation storage/key contract jointly before final release acceptance.
- PR25 migrations require L1 guarded target selection and disposable DB only; do not run on operational DB. PR25 frontend changes must be preserved.
- Reference legacy security test was updated in PR27 to verify guards emit metadata, do not commit; durable two-event check is required in real writer PG HTTP gate, not merely spy.

## 4. Event ownership matrix
Guard require_permission/require_organization: check and raise AuthorizationDenied metadata; NO commit/rollback.
FastAPI get_db transaction owner: rollback business transaction, then invoke writer once; preserve failure (never mask or silently ignore writer errors).
PR25 record_outcome_independent: validate existing server-side actor/tenant, sanitize details, independent SQLAlchemy Session and commit, error propagation.
PR25 contract create/revision: successful business event in business transaction; for authorization 403 do NOT duplicate owner event; for business 409 after rollback one contract-domain denied event with documented reason.
Anonymous auth failures: separate contract decision pending, no invented actor.
UI hides edit without write permission, API independently enforces reference.write.

## 5. Before-authorized-merge checklist (future, NOT executed)
1. Freeze exact two PR heads and source blob SHAs, review PR25 owner's acknowledgment.
2. Create independent integration branch from PR25 HEAD only after central approval.
3. Compose PR27 change-set; inspect/resolve app.py and any concurrent overlaps; preserve both sets of migrations/routes and tests; record merge provenance.
4. Assert no missing import mcias.audit_writer in checkout without untracked overlays. Build from clean git clone.
5. Provision strictly synthetic disposable PG16; apply Alembic after safety check; run integrated Enterprise, Contracts acceptance (Chromium/API), dedicated L2 PG guard, L2 real-writer HTTP, G1–G7, G8, G9 and dependent CI, all on one exact integration SHA. Read denial traceback/actual audit rows and verify 403 not 500.
6. Verify denied business mutations not persisted, exactly 1 durable event per attempt in independent Session, tenant isolation, no PHI/secrets, duplicate routes/retries, anonymous cases policy decision.
7. Save CI artifact links and DG-001 Worklog/HANDOFF; request independent review only. NO main merge/deployment.

## 6. Evidence retained
Baseline original PostgreSQL FAIL: https://github.com/overurdream-collab/test2/actions/runs/39257009551
Post-fix no business commit PASS: https://github.com/overurdream-collab/test2/actions/runs/39257480016
PR27 real writer temporary HTTP PASS: https://github.com/overurdream-collab/test2/actions/runs/39305148030
PR27 Enterprise original missing import FAIL: https://github.com/overurdream-collab/test2/actions/runs/39305148046
PR27 isolated Enterprise real-writer composition PASS: https://github.com/overurdream-collab/test2/actions/runs/39305147985
Status: integration deployment BLOCKED until contract decision, actual branch composition, all required gates and approved source dependency are verified.
