# DG-001 — PR #25 contract-edit L2 security checkpoint / Worklog + HANDOFF
Date: 2026-10-19. Owner: Input UI and shared services. Scope: PR #25 only.
Baseline exact SHA: `60f1db7d174e9d1a29921ed578392ed5705b2874`.
PR #27 security reference: `a0dc6cf993b1c3082f85df1b7bca1287dda16226`.
**Status: PARTIAL / BLOCKED; UI visibility requirement FAIL. No merge/deployment.**

## Worklog — verified inspection
- Verified GitHub PR #25 HEAD equals baseline SHA; PR remains draft/open. PR #27 also draft/open; not modified.
- Actual G3 edit exists in `mcias/web_workspace/views.js` (contract selector and `editG3ContractDraftForm`), POST `/api/v1/reference/contracts/drafts/{id}/revise` in `mcias/reference_api.py`, and append-only `revise_contract_draft` in `mcias/reference_service.py`. Only numbered draft contracts can be revised; the historical row remains.
- **FAIL**: `actionButton` lines 123–131 and contracts toolbar around 2919–2933 *disable* Edit for missing `reference.write` but keep it visible. Strict Chromium `scripts/check_contracts_acceptance.py` lines 86–93 explicitly checks `to_be_disabled()`, not `to_be_hidden()`. Current strict CI success must not be reported as PASS for the stronger requested UI requirement.
- **PASS (existing synthetic CI)**: strict Chromium+FastAPI+PostgreSQL16 validates authorized G3 revision and database historical row, denial of reader's direct revision HTTP POST with 403, stale 409, invalid dates 409, denial audit persisted after rollback for tested stale rejection, audit metadata redaction and a single revision success audit. Exact-SHA run: https://github.com/overurdream-collab/test2/actions/runs/39143195130
- **PARTIAL/BLOCKED**: cross-tenant G3 revision through a direct authenticated write request against a foreign organization's contract is NOT explicitly exercised by the current strict harness. The synthetic foreign-tenant audit read isolation test at lines 329–350 is **not** a cross-tenant contract-write test.
- **PARTIAL**: reader revision 403 is checked, but no direct assertion that this *specific reader edit rejection* creates exactly one independent durable audit record. `revise_contract` calls `_actor` before its local try/except (reference_api.py lines 228–245). Existing `require_permission` / `require_organization` guard code on this branch can independently commit denial events; the PR #27 transaction-owner rollback and deduplication contract remains a separate owner dependency. Never infer atomic rollback+one event across all denial paths.
- Shared `mcias/audit_writer.py` exists and is callable: `write_event` stages success in business transaction; `record_outcome_independent` commits in separate session after caller rollback; details allowlist strips arbitrary fields. Existing creation and revision G3 integrations are evidenced by strict CI. **Not yet approved as fully integrated generic denial writer for PR #27**: request-transaction-owner rollback, correlation/deduplication across guards, and cross-tenant failure scenarios require composition/integration review.
- CI on same baseline SHA: G1–G7 https://github.com/overurdream-collab/test2/actions/runs/39143195117 PASS; G8 https://github.com/overurdream-collab/test2/actions/runs/39143195094 PASS; G9 https://github.com/overurdream-collab/test2/actions/runs/39143195039 PASS; Enterprise https://github.com/overurdream-collab/test2/actions/runs/39143195152 PASS. These runs establish only the checks they contain.
- Historical acceptance worklogs, original tests and failure evidence retained unmodified.

## HANDOFF — DG-001
- IDENTITY: PR #25 input UI and shared audit service owner.
- GOAL: satisfy visibility, direct API denial, no business mutation, durable bounded audit exactly once, tenant isolation.
- DONE: exact-SHA inventory, CI review, actual G3 edit path and shared writer interface identified; gaps classified without fabrication.
- NOT DONE: change hidden-Edit UI requirement, new real browser visibility assertion, explicit foreign-tenant direct G3 revision denial+DB readback, exact-one durable audit on reader 403, PR #27 combined regression.
- BLOCKERS: PR #27 owns FastAPI request rollback/guard changes; do not cherry-pick or edit that branch. Coordination with central security supervisor needed before cross-owner audit/guard contract changes.
- NEXT (PR25-local): under narrowly scoped authorized UI work, hide Edit for nonwriters and add browser test with `to_have_count(0)`, plus an authorized selected-contract visibility test; add isolated foreign-tenant synthetic POST+readback test if allowed by test fixture. Treat any shared guard redesign as outside PR25 scope and escalate.
- NEXT (PR27 owner): request-owned rollback before independently committed audit, ensure one logical denial and no pending writes, test actual cross-tenant guard in disposable PostgreSQL16 and CI composed with the exact PR25 writer. Do not equate a hypothetical CI run with verified PASS.
- NO merge, NO deployment, NO writes to main or PR #27.

## Follow-up implementation — 2026-10-19, central supervisor authorized
- Baseline inspected `421963abf2770db8f477b7f15be0b3517030beb2`; no concurrent head divergence before edits.
- `05476628d3b4c8b16638bd496f5548c6f3419d45`: contracts toolbar completely omits Edit for actor lacking effective `reference.write`; leaves other sections and RBAC unchanged.
- `4ce8426a57e533b9844cf7aaa269d79d6973f660`: existing strict real Chromium test now asserts no reader Edit DOM control (count zero) and authorized writer visible/enabled after selecting G3 draft. Added synthetic foreign-organization draft, direct POST revision attempt with writer token for another organization, independent PostgreSQL readback of all original fields, only original version remains, and exactly one sanitized `contract_revision_denied` audit event for this conflict path. Rejection may be 403/404/409 per existing API contract; current service raises ReferenceConflict (409). This proves denial only if exact-SHA CI passes.
- Historical tests untouched except the specific stricter visibility check and appended foreign-tenant assertions.
- PR27 coordination request posted on its conversation: https://github.com/overurdream-collab/test2/pull/27#issuecomment-6274174816 . PR27 branch unmodified. Request: exact writer + PostgreSQL, request-owned rollback, single sanitized denial event and no pending changes; distinguish permission-guard 403 from foreign revision business conflict 409.
- GitHub automatic CI on `4ce8426a57e533b9844cf7aaa269d79d6973f660` observed in progress, strict run https://github.com/overurdream-collab/test2/actions/runs/39301649100, G1–G7 https://github.com/overurdream-collab/test2/actions/runs/39301649172, G8 https://github.com/overurdream-collab/test2/actions/runs/39301649129, G9 https://github.com/overurdream-collab/test2/actions/runs/39301649048, Enterprise https://github.com/overurdream-collab/test2/actions/runs/39301649160.
- **Acceptance pending CI final status**. PR27 combined guard+writer PostgreSQL integration evidence belongs to PR27 owner and is BLOCKED until confirmed. No merge or deployment.

## HANDOFF update
- DONE: targeted UI code, real Chromium assertions, foreign-tenant synthetic API/DB/audit test, PR27 coordination.
- VERIFY: await completed strict browser+PG16 exact-SHA run and inspect job/artifacts. Never claim PASS for unexecuted/new CI.
- OUT OF SCOPE: modify RBAC, generalized guard, PR27 files, main, merge or deployment.
