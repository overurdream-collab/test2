# DG-001 — W1 Windows UI reuse pilot — 2026-10-20

Status: ISOLATED / FINAL W1 TEST GATES PASS / DRAFT INDEPENDENT REVIEW PENDING. No production deployment or merge.

## Source and baseline
- main: b69defa2f621458ef44d790b510840307a81009a
- Windows source: 50ffd4bfd58661137cf079f99058159eb831e588 (PR #17)
- Pilot branch: feat/mcias-w1-windows-ui-reuse-pilot, created from main.
- Windows 11 Docker execution was confirmed by the owner and is not being repeated.

## Verified UI inventory
- Shared with main: mcias/web_workspace/app.js, views.js, workspace.css, routes.json. Do not replace wholesale.
- Windows-only: institution.js (175 lines), feature_navigation.js (65 lines). Both reference Windows-only API/feature contracts.
- Windows source includes advanced RBAC, Ed25519 approvals, registry service and migrations; explicitly excluded.
- Four W1 targets: sidebar/navigation, institution overview, institution users UI, shared UI primitives.

## Compatibility gate / findings
- The institution.js source depends on institution overview/users APIs and feature-based grants absent from main; direct copying would produce broken UI and could weaken permission semantics.
- Existing main shared UI components should remain authoritative. Do not create a second component library.
- The source route inventory is 97 routes, versus 59 on main. Route availability metadata is not proof of backend support.
- Admin grant and role changes must remain exclusively under Super Admin authority. UI visibility is never server authorization.
- Do not copy any backend, RBAC provisioning, Ed25519, registry, audit middleware, migrations, OCR or agents.

## Pilot verification state
- Historical Windows CI at SHA 50ffd4b: G1-G7, G8, G9, Enterprise, Windows launcher and Docker succeeded; they do not validate W1.
- W1 browser/permissions/tenant isolation tests: NOT RUN.
- W1 adapted UI components: NOT YET IMPLEMENTED.
- No new migration, production database, patient data or deployment used.

## HANDOFF
Implement a narrow, API-safe, main-native UI adapter. Start with route visibility using existing main permission contracts, then read-only institution dashboard, then users read-only UI. Mark unsupported actions unavailable rather than mock-authorized. Keep existing app.js/views.js/workspace.css authoritative and preserve AR/EN, RTL/LTR, light/dark and responsive layouts. Add focused Node tests and browser tests against synthetic data. Only create a Draft PR after tested UI code is available.

## Decision
W1 pilot is NOT COMPLETE. No integration or production acceptance authorized.

## W1 implementation continuation (2026-10-20)
- Source HEAD reverified: Windows 50ffd4bfd58661137cf079f99058159eb831e588; pilot started from f663cd5e7698b7d6b984ceacc8ba24c1e6ed9ee1.
- Adapted Windows feature_navigation.js pure route matching/grouping to mcias/web_workspace/w1_navigation.js; uses main permissions, never Windows feature entitlements.
- Modified main app.js minimally: filtered navigation/search, route matching and authorization presentation; server API remains authoritative.
- Adapted institution.js overview hero/cards into views.js and kept existing main protected report-snapshot dashboard as source of all metrics. No Windows backend or synthetic operational figures.
- Adapted institutionUsers visual pattern into read-only /admin/users cards with local search/status filter, main /api/v1/workspace/catalog/users API; no POST/PATCH/DELETE actions.
- Added focused Node tests tests/w1_navigation.test.mjs.
- IMPORTANT: W1 tests and browser tests are NOT YET EXECUTED. API tenant isolation and negative server authorization NOT VERIFIED in this pilot. UI adaptation is not accepted until tested.
- Main /institution/users route does not exist; users UI remains on main /admin/users and is Super Admin-gated, not a newly invented institution users API.
- No RBAC, signatures, migration, audit middleware, registry, AI or deployment changes.

## HANDOFF next actions
1. Run node --test tests/w1_navigation.test.mjs; fix failures.
2. Run JS syntax/import checks and browser synthetic authenticated flows at desktop/mobile AR/EN, RTL/LTR, light/dark.
3. Verify actual server-side 403 and tenant isolation against authorized main API with synthetic PostgreSQL; if unavailable mark unverified.
4. Run relevant regression subset and check CI results on final SHA.
5. Open Draft PR only after passing tested UI changes; do not merge or deploy.

## Focused verification result — 2026-10-20
- GitHub Actions Run #39344501343, SHA 28e65b95c4287fbeba6f52ac476af01c30f95a1f: SUCCESS. URL: https://github.com/overurdream-collab/test2/actions/runs/39344501343
- Steps completed successfully: node --test tests/w1_navigation.test.mjs; npm run check; node --check mcias/web_workspace/w1_navigation.js; npm test (10/10 passed, zero skipped).
- Verified source: GitHub Actions job 118373729559 logs. CI Node deprecation warning is non-blocking.
- NOT RUN / NOT VERIFIED: real-browser desktop/mobile flows, AR/EN RTL/LTR and theme in browser; PostgreSQL synthetic negative API auth and cross-tenant isolation; browser UI search/status/loading/error behavior. These remain acceptance blockers.
- No Draft PR yet because mandatory browser/security gates are not evidenced. No merges or deployment.


## W1-FINAL-VERIFY resumed — 2026-10-20
- Reverified W1 branch HEAD before changes: d4798a3dfac67c115f181846023db9c5fd40525f; no reset or modifications to other branches.
- Accepted existing W1-T1 GitHub Actions Run #39344578716 on that exact SHA: SUCCESS. No Node test rerun requested.
- Existing reusable browser suites confirmed: scripts/check_workspace_browser.py (Chromium AR/EN, RTL/LTR, themes, responsive, mock API), scripts/check_workspace_live.py (real server login, PostgreSQL claim reads, logout). Existing tests/test_enterprise_workspace.py includes negative 403 authorization, tenant-scoped reads, super_admin + users.read gating, sensitive-field checks.
- Created .github/workflows/w1-browser-security.yml on W1 branch, commit d79306c2c842bac364864b68983cabdc3d1fe24f. Isolated PostgreSQL 16 service, Chromium, synthetic fixture, existing pytest security tests and both existing browser scripts, screenshot and JSON evidence upload.
- IMPORTANT: Creating a workflow is NOT a successful execution. Chromium/PostgreSQL results and three-role real browser acceptance remain UNVERIFIED until a completed GitHub Actions run demonstrates them.
- The existing browser scripts do NOT establish a three-role real-session matrix; they cover mock reader and real reader session. W1-T2 full Super Admin/Admin/User browser matrix is therefore still an explicit gap.
- /admin/users uses the current Super Admin read-only UI and existing users catalog; /institution/users is not implemented and is not claimed complete.
- No Draft PR or production acceptance until actual successful browser/security evidence is checked. No deployment or merge.


## W1 final role matrix extension — 2026-10-20
- Previous isolated Chromium/PostgreSQL 16 Run #39401345142 completed SUCCESS at SHA d79306c2c842bac364864b68983cabdc3d1fe24f; W1 Node Run #39401365910 completed SUCCESS at c865138f8c9477c8ba07dd7991e9574dee1813a5.
- One targeted UI compatibility fix: w1UsersReadOnly() uses the server's existing boolean `active` rather than absent `status`; filter and display use active/inactive mapping. No backend contract changes.
- Reused scripts/check_workspace_live.py, adding actual FastAPI login with synthetic PostgreSQL sessions for super_admin (real encrypted MFA/TOTP), admin, and existing reader; navigation/RTL-LTR/mobile, Super Admin-only /admin/users, server API 403, foreign-organization user detail 404 and bounded current-organization list, plus synthetic screenshots and JSON role matrix.
- Existing PostgreSQL/Chromium workflow now preserves .e2e-output/w1-role-matrix.json and per-role screenshots. Current role-matrix verification Run #39402706752 at SHA c8114507a0c42ff05ac568703a25058e3fd6e65c was triggered; final PASS/FAIL must be determined from the completed run, not from this document.
- /institution/users remains unsupported for Admin. No RBAC/Ed25519, migrations, production data, deploy or merge. Draft PR withheld pending completed mandatory security evidence.

## W1 synthetic CI blocker fix — 2026-10-20
- Confirmed failed Run #39402706752: existing server tests and browser baseline passed; role matrix stopped at AESGCM MFA fixture setup (ValueError: invalid AES key length).
- Workflow now uses 64-character hexadecimal synthetic values (32 bytes) for both MCIAS_MFA_ENCRYPTION_KEY and MCIAS_STORAGE_KEY, with a fail-fast no-secret-print validation step. No application cryptography changed.
- Existing role-matrix fixture grants reports.read only to synthetic Super Admin and Admin to satisfy institution dashboard access. No production role or server permission changes.
- Test code SHA d0acb615de1798f14114697c3c24c1c02b7f1668; focused rerun #39404129037 was in progress at documentation time. A completed PASS is mandatory before Draft PR; do not interpret this handoff as acceptance.
- The Admin-specific /institution/users route remains absent; the current experiment does not implement it.

## W1 final role-matrix selector correction — 2026-10-20
- HEAD verified at 0c46f531df25b131ec7c4aa422ed630a664442a9 before change; the saved f['organization_id'] fix and AES-256 fixture keys were already present and were not repeated.
- Run #39405315426 failed at scripts/check_workspace_live.py:114, Playwright Locator.select_option timeout: #w1-users-status does not exist because ui.js field() generates random DOM IDs and retains name="w1-users-status".
- Changed only the two selectors in the existing live test to select[name="w1-users-status"]; commit 0b80a4513bc39c034f3299e14073db8dfc9eed11. No UI/backend/security-contract changes.
- Isolated PostgreSQL 16/FastAPI/Chromium rerun #39480364000 triggered at that commit; final matrix and screenshot artifacts require a completed successful run. Draft PR remains gated on those results.

## DG-001 — W1 final verified result (2026-10-20)

**Scope:** W1 isolated Windows UI reuse pilot; synthetic-only, read-only management interface. This section supersedes historical pending/not-run statements above as to the **current test status only**. It is **not** production approval, permission to merge, or authorization to deploy.

- **Functional code/test SHA:** `0b80a4513bc39c034f3299e14073db8dfc9eed11`.
- **Completed required browser/security workflow:** [W1 Chromium + PostgreSQL 16, Run #39480364000](https://github.com/overurdream-collab/test2/actions/runs/39480364000): **SUCCESS**, same functional SHA.
- **Node/UI workflow:** [Run #39480363982](https://github.com/overurdream-collab/test2/actions/runs/39480363982): **SUCCESS**, same functional SHA.
- **Server authorization and tenant isolation:** `tests/test_enterprise_workspace.py` **72 passed, 1 warning** (Starlette/httpx deprecation only), no mandatory test SKIPs.
- **Real Chromium/FastAPI/PostgreSQL 16 flow:** `scripts/check_workspace_browser.py` and `scripts/check_workspace_live.py` completed successfully. Historical mock-based browser coverage is supplementary, not substituted for the real-session role matrix.
- **MFA:** real synthetic Super Admin login with TOTP/encrypted MFA fixture passed. The two synthetic 32-byte test keys passed the dedicated preflight length validation; no application cryptography change.
- **Evidence artifact:** [Run #39480364000 — w1-chromium-postgres-evidence (artifact #12290428522)](https://github.com/overurdream-collab/test2/actions/runs/39480364000/artifacts/12290428522), 15 archived files according to the successful upload log; contains `.e2e-output/w1-role-matrix.json`, per-role screenshots `w1-super_admin-users.png`, `w1-admin-users.png`, `w1-user-users.png`, plus browser/real-session result outputs. Artifact SHA256 digest: `0825c97e351090272ee78cb2be46457d9b2ecffa9d0e012f294220af71562604`.
- **Security assertions skipped:** `0` as reported by the completed role-matrix script.

### Actual synthetic role matrix — PASS/FAIL

| Verified requirement | Super Admin | Admin | User |
| --- | --- | --- | --- |
| Real authenticated session through FastAPI | PASS | PASS | PASS |
| MFA on Super Admin session | PASS (TOTP) | Not applicable | Not applicable |
| Dashboard and navigation AR/EN, RTL/LTR, desktop/mobile | PASS | PASS | PASS |
| `/admin/users` UI authorization | PASS (read-only cards, no edit/delete buttons) | PASS (access denied) | PASS (access denied) |
| `GET /api/v1/workspace/catalog/users` | PASS (HTTP 200, scoped fields) | PASS (HTTP 403) | PASS (HTTP 403) |
| `GET /api/v1/workspace/users/{foreign_user_id}` | PASS (HTTP 404) | PASS (HTTP 403) | PASS (HTTP 403) |
| Tenant isolation | PASS | PASS | PASS |
| Current active/inactive filter bound to API boolean `active` | PASS | Not authorized | Not authorized |

All values above are corroborated by the successful workflow execution and its printed role matrix. Super Admin is the only sensitive administrative authorizer in current W1. The non-existent `/institution/users` route remains out of scope.

### HANDOFF — independent review / stop point

1. **Acceptance gate for an isolated Draft PR:** all required W1 CI checks **PASS**, no security skips, JSON/screenshot evidence retained in the linked workflow artifact. Open a **Draft PR only** for independent review.
2. **Independent reviewer focus:** server-side 403 enforcement independently of hidden navigation; Super Admin read-only management UI; TOTP and tenant boundaries; boolean `active` status mapping; responsive AR/EN navigation; test-only permissions and key fixtures.
3. **No further W1 coding required for this test scope.** Preserve the existing W1 branch and CI results. Changes in this handoff are documentation-only and do not justify rerunning already successful functional tests.
4. **Boundaries:** no merge, deploy, production database/patient data, backend RBAC change, Ed25519, `/institution/users` implementation, Shared Audit, or migration changes. Any future integration/rebase needs separate review of current `main` and other active branches.
