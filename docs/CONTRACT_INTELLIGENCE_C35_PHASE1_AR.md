# C35 Phase 1 — Deterministic Source-View Adapter
Status: IMPLEMENTED / CI PENDING. PR #23, base `eb48880abf0cf6e0ec227c1981a39a87bd1d3d8a`. No Qwen/model calls, Reference Selection, Resolver, Validator/Gold changes, DB migration, tariff approval or production wiring.

## Implementation
- `mcias/contract_source_view.py` is a standalone, read-only adapter over already produced `make_source_blocks()` G2 blocks; no inference imports or integration into existing contract path.
- Preserves every retained literal source value and original locator; adds field name (including A1 cell name when supplied by G2), original record ID, row/segment group ID, supplied source SHA256, and deterministic SHA256-derived field ID based on document digest + record + full locator + field name. Repeated values across columns/rows remain distinct.
- `make_source_blocks()` intentionally drops whitespace-only cells and truncates fields at 3000 characters; this adapter promises literal fidelity to the **existing G2 blocks**, not restoration of raw pre-G2 cells. No fabricated source cells or currency.
- G2 sheet row locator must contain row number; without row identity adapter fails closed. A1 cell coordinates can only be preserved if G2 supplies them (field names or locator), never inferred.
- The view's `field_type="text"` is conservative and does not infer currency/amount/service semantic types. A Phase 2 selector may use the explicit source field names but is NOT implemented.
- Duplicate record+locator rejected, unknown field IDs fail closed. No cross-row concatenation or generated quote.
- Test matrix: R1–R6, C33 mixed-provider segment locators, R5/R6 Excel row boundaries, blank fields, repeated amounts, ambiguous OCR digits, duplicate addresses, bad locators, bad references, and original Validator unchanged.
- Existing C33/C34 model runs are not repeated. Dedicated lightweight deterministic CI: `.github/workflows/contract-ai-c35-source-view.yml`. Report exact SHA/run outcomes after GitHub finishes.

## DG-001 HANDOFF
OWNER=Contract Intelligence PR23; SCOPE=isolated deterministic phase 1; STATUS=CI_PENDING; NEXT=inspect exact-SHA C35 CI, verify tests PASS and reference workflow checks; no model or production changes; do not proceed to Phase 2 without approval.
