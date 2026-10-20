# DG-001 — Manual G3 contract add acceptance — 2026-10-18

Parent: 9ee22ac6efc6b7fc0b24e41919c046dabb818c16; Draft PR #25; contracts only.

## Existing services examined
The "Add" toolbar previously launched generic InputClause create rather than G3 /api/v1/reference/contracts. G3 already enforces organization, reference.write, valid temporal boundaries and draft-only creation through reference_service.create_draft; G3 financial approval is a separate, signed workflow. The G3 ContractVersion lacked independent contract number and textual metadata.

## Narrow implementation
- Rewire only "contracts" Add to an organization-bound G3 draft form with contract number, provider code, effective dates, contract notes and precedence. Organization is derived from authorized session, never user-supplied.
- Add optional non-financial contract_number and contract_notes to G3 ContractVersion via additive migration 0020_manual_contract_metadata; allow legacy callers (optional number) and enforce unique org/contract number/version. Existing temporal and signed-financial approval checks unchanged.
- Reuse current G3 create_draft; preserve draft-only status. Add tenant-scoped readback GET /api/v1/reference/contracts/drafts/{id}, and authorized existing workspace catalog contract metadata.
- Browser form makes actual POST then authorized GET and checks saved fields/status before displaying a successful response.
- Strict Chromium + PostgreSQL test uses distinct synthetic contract number, checks form and readback, DB row, original import regression, denied reader POST (403), duplicate number (409), invalid date range (409), and no authorization/approval.
- Artifact screenshots: 07-manual-add-empty.png, 08-manual-add-filled.png, 09-manual-add-saved-and-read.png; JSON results include manual_add_db_evidence and validation HTTP codes.

## Boundaries
G3 contract details are **not** the InputClause record type. No aliasing provider code to contract number; no unsupported contract field fabrication. No G3/G5 approval change, no production deployment/merge, no Edit workflow, no other sections. PASS only from exact-sha strict Actions run, not from code presence. Current date's test fixtures are synthetic and local to ephemeral PostgreSQL. Revision migration is additive and intentionally not destructively reversible.
