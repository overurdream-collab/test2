# DG-001 — Input tri-action implementation checkpoint
Date: 2026-10-18
Branch: `feat/mcias-input-triactions-e2e`
Parent: `feat/mcias-temporal-inputs-triage-ui` (NOT main)
Related: #24, temporal input work PR #22.

## Change and rationale
Existing temporal input workspace already has eight sections, source upload, a governed create endpoint, record list and append-only revision via `replaces_id`. Avoided new data model and sweeping redesign. Added a stable three-action row per section with Import (clearly labeled *source upload*), Add, Edit. Edit is disabled until an authorized record is selected by its evidence/detail action; selection clears on switching sections or reloading. The previously existing per-record revision remains.

## Controls held
- No fabricated extraction success; PDF/XLSX/CSV/image upload only stages a source. Extraction/preview/validation before commit and bulk import **are NOT implemented** by this patch.
- No direct mutation of approved/historic records. Revision continues via POST with `replaces_id`, subject to server authorization.
- Client controls follow existing `reference.write`, `ingestion.upload` effective-permission gates. Server RBAC must still be tested.
- RTL/LTR localized action labels and shared fixed toolbar placement.
- No institution policy activation, no production patient fixtures, no deployment, no merge to main.

## Delivery acceptance matrix (status at code inspection, NOT E2E)
| Section | Import | Add | Edit |
|--|--|--|--|
| Contracts | Partial — source upload | Partial — POST clause draft | Partial — revision POST |
| Providers | Partial — source upload | Partial — POST clause draft | Partial — revision POST |
| Beneficiaries | Partial — source upload | Partial — POST clause draft | Partial — revision POST |
| Copays | Partial — source upload | Partial — POST clause draft | Partial — revision POST |
| Categories | Partial — source upload | Partial — POST clause draft | Partial — revision POST |
| Exclusions | Partial — source upload | Partial — POST clause draft | Partial — revision POST |
| Approvals | Partial — source upload | Partial — POST clause draft | Partial — revision POST |
| Tariffs | Partial — source upload | Partial — POST clause draft | Partial — revision POST |

Partial means code-path exists; there is no proof of real DB readback for this patch.

## Verification and blockers
Static repository source assertions added to `tests/frontend/input-triactions.test.mjs`. No execution of Node, PostgreSQL, FastAPI, browser test suite or screenshot capture was available in this environment; no pass results claimed. Before acceptance: run `npm test` and `npm run check`, Python regression suite with PostgreSQL test URL, eight-section seeded browser/API/DB readback scenarios (positive/negative RBAC, revision immutability and tenant isolation), actual AR/EN desktop/mobile screenshots, upload extraction review, file validation and audit-event checks. Reevaluate DG-001 approval controls and actual backend capabilities before enabling any feature labeled complete.

## No-go gates
Do not approve or merge until all 24 real flows pass and upload preview/validate exists. Do not deploy absent explicit user approval.

## Contracts-only follow-up — 2026-10-18
Scope deliberately restricted to **contracts**. Commit `39ef76e59a60009f46a0867983c749670b8dcd58` adds an explicit button to read the existing G2 ingestion source manifest after uploading a contract, when the upload service returns a syntactically valid document identifier. This is a **source-manifest inspection**, NOT extraction of structured contract terms, a contract preview/validation workflow, or successful contract persistence. No contract is automatically activated.
The prior branch already exposes Add via the section-specific `/api/v1/input-clauses/points` request, Edit by `replaces_id`, plus separate G3 contract draft POST. These are not equivalent data models and must not be conflated without source inspection and contract identification/version rules.

Acceptance still blocked:
- G2 contract-specific parsing and field-level source-linked candidate extraction/validation not demonstrated.
- No actual synthetic PDF/XLSX ingestion run or quarantine/negative examples.
- No browser end-to-end role matrix, PostgreSQL roundtrip, immutable original/version history verification or screenshot evidence.
- CI run status not certified by this documentation.
Do not claim Import/Add/Edit works. Do not extend to seven other sections, merge to main, or deploy.
