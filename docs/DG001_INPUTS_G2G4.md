# G2 + G4 INPUTS-FIRST — owner handoff

Date: 2026-10-21. Baseline HEAD: `bd2d1b0c92a5410466217802be936dd469b3b35f` (PR #31). Branch: `codex/inputs-first-g2-g4`. Scope: coordinated minimal implementation and synthetic verification only. No merge, deployment, production migration or real patient data.

## Finding and adopted contract

E1 previously imported one CLAIMS row because PAYMENT failed normalization, leaving `review_required`; this did not prove an approved CLAIMS-only gate. The revised E1 deliberately gives PAYMENT all required valid claim columns, so only explicit source classification can exclude it.

The coordinated interface approved by the parent is `approve_source_scope(db, actor, document_id, sheet_types: dict[int,str]) -> AuditLog`. An existing `claims.import` permission and active database-backed same-organization actor are required. G2 records the actual worksheet name/index, physical row, raw extracted strings and full worksheet inventory. Human scope approval binds document/source SHA-256, extraction job, canonical `g4-canonical-v1` mapping, and a SHA-256 fingerprint of the inventory and every record/locator/value. It is an append-only `claim_source_scope_approved` event; raw values and sheet names are excluded from event details. The existing protected source registry and encrypted original retain the evidence.

Only explicitly classified CLAIMS rows enter the existing G4 importer; PAYMENT/FAMILY_SUMMARY/OTHER stay in the source registry. UNKNOWN, incomplete classification, changed source/inventory/records, and missing approval block import. Reserved PAYMENT/FAMILY_SUMMARY sheets cannot be relabeled CLAIMS. `stage`, `preview`, and `resume`, including retries after completion, revalidate the approval. `ClaimBatch.record_count` is eligible claim rows; returned excluded counts reconcile nonclaims. Imported locator JSON records document/job/source SHA/approval/mapping and CLAIMS type without a database migration. `source_scope(db,actor,document_id)` returns revalidated lineage/eligible and excluded record IDs for G5. An authenticated existing claims API endpoint accepts only typed sheet classifications: `POST /api/v1/claims/documents/{document_id}/source-scope`.

## Owned files

- `mcias/ingestion/schemas.py`, `mcias/ingestion/parsers/excel_parser.py`, `mcias/ingestion/provenance.py`, `mcias/ingestion/manifest.py`.
- `mcias/claim_batches.py`, `mcias/claims_api.py`.
- `tests/test_g4_approved_source_scope.py`, `tests/test_e1_real_g2_g4_pg16.py`.
- This report, append-only execution journal and current-state overlay.

## Actual verification

- Earlier focused regression command: `PYTHONPATH=. /workspace/.venv/bin/python -m pytest -q tests/test_g2_reader.py tests/test_g2_ingestion.py tests/test_g4_batches.py tests/test_g4_normalization.py tests/test_e1_g2_cai01_synthetic_boundary.py tests/test_cai01_batch_preflight.py` — **43 passed**.
- Parent independently ran current owned tree against isolated PostgreSQL **16.15** database `mcias_inputs_g2g4`, using `MCIAS_TEST_DATABASE_URL`, development/disabled-malware synthetic configuration and `PYTHONPATH=.`: `python -m pytest -q tests/test_e1_real_g2_g4_pg16.py tests/test_g4_approved_source_scope.py tests/test_g4_batches.py tests/test_g2_ingestion.py` — **21 passed in 4.66s**, one Alembic deprecation warning. The first attempted agent PG tool call hung and was aborted; no result is claimed from that call.
- E1 performs real G2 ingest, exact encrypted-original recovery and source SHA checks, scope approval, native G4 stage/preview/resume, Commit and independent-session ClaimEntry reread. It proves one preserved CLAIMS source row, one excluded valid claim-shaped PAYMENT row, one scope approval on repeat, no duplicate claim on retry, and organization isolation for stage/preview/resume/source lookup.
- Negative source-scope tests cover absent grant, missing/unknown/partial classifications, forbidden PAYMENT relabeling, immutable approval, edited values/name/inventory/original SHA and revalidation after completed import.
- `git diff --check` passed. Commit SHA is the commit containing this report; CI links will be supplied by parent after publishing the coordinated draft branch. No CI success is inferred from these local runs.

## Limits and closure

The minimal interface supports the existing canonical G4 columns; it does not create arbitrary mapping, a new importer, or new financial decisions. CSV behavior remains the established G4 contract. Existing extraction quarantine still blocks staging; no quality bypass was added. Large-scale throughput and all G3/G5/Shared Audit integrated acceptance are outside this owner's proof and require the coordinator's native-service run. First remaining dependency: root/G5 must compose this producer with the G3 certificate and shared writer commits and run the full synthetic PG16 flow on the final combined SHA. No owner-local blocking failure remains in the tested scope.
