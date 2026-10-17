# DG-001 — Contracts-only acceptance evidence review (2026-10-18)

## Exact scope and provenance
Repository: overurdream-collab/test2; Draft PR #25; inspected SHA: `7bdc5f5ca958e6be27741235b042aee4398862e2`.
NO production deploy or main merge. This is an evidence review, NOT an acceptance signoff.

## GitHub Actions actual evidence
- G1–G7: run 39075264513, reported successful.
- Enterprise: run 39075264474, job 117521007115 `browser-and-contracts`, reported successful.
- Log contains `367 passed, 1 skipped, 14 warnings` for the Python suite; Chromium browser runtime and PostgreSQL 16 were installed/used by the workflow.
- Browser script `scripts/check_workspace_browser.py` declares synthetic demo mode; `scripts/check_retention_browser.py` does a real DB-backed browser login and retention flow. Neither demonstrates the requested contract Import/Add/Edit acceptance lifecycle. Workflow green is **not** proof those three workflows pass.
- E2E evidence for contracts-specific user actions, DB row readback, authorized/unauthorized actor, G2 contract structured extraction, and real screenshots: NOT PRESENT in inspected run.
- Links: https://github.com/overurdream-collab/test2/actions/runs/39075264513 and https://github.com/overurdream-collab/test2/actions/runs/39075264474

## Exact blocker
Current contract import UI (`mcias/web_workspace/views.js`, `uploadClauseSource`) submits raw source to `/api/v1/ingestion/uploads`, then permits an optional `/api/v1/ingestion/documents/{id}/manifest` read. The returned manifest does **not** itself provide a field-level extracted contract proposal, user-editable preview, source-backed validation, or explicit confirm-before-create. The frontend itself describes automated clause extraction as not activated. Accordingly, merely uploading a PDF/XLSX and opening the manifest cannot satisfy contract import acceptance.

Separate add/create and revisions are wired in UI to `POST /api/v1/input-clauses/points`, with `replaces_id` for edits; but no performed browser→PostgreSQL roundtrip or independent version-history assertion was found in these logs. Do not assert PASS from source wiring.

## Acceptance results
| Action | Status | Required missing evidence |
|---|---|---|
| Import PDF/XLSX via G2, parse terms, preview, validate prior to approval | **BLOCKED** | Field-level G2 extraction and human preview/validation in browser; actual synthetic upload |
| Add contract manually, PostgreSQL write then readback | **BLOCKED** | Authorized Chromium form submission, PostgreSQL row readback, unauthorized denial |
| Revise existing contract, prove original preserved and new version present | **BLOCKED** | Browser edit, DB two-version comparison, denied unauthorized revision, version audit history |

## Execution access limitations
This session can read and modify GitHub through the connector but cannot clone over HTTPS locally (DNS resolution of github.com failed). Existing hosted CI works; however its executed scenarios do not cover contract-specific end-to-end acceptance. A dedicated test must be committed that FAILS on any unproven import/add/revision behavior, run in Actions with its ephemeral PostgreSQL service and Chromium, and archive raw screenshots/SQL readbacks. No CI completion or screenshots for that dedicated test are claimed here. Do not weaken acceptance criteria merely to green CI.

## Hold points
No new features introduced during this evidence review. Do not test other input sections, merge main, deploy, change financial policies, or declare DG-001 acceptance.