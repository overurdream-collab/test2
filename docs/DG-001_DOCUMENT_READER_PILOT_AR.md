# DG-001 — Document Reader isolated extraction pilot (2026-10-20)

Status: EXPERIMENTAL / NOT accepted for production or medical/financial use.
Branch: feat/mcias-document-reader-isolated-pilot, created from main. No edits to ingestion, Shared Audit, L1, contracts, or production data.

## Verified current code
- mcias/ingestion/orchestrator.py runs checksum/dedup, storage, malware scan, identify, isolated_parse, Palermo-1, extracted records with Locator, quarantine and an audit write.
- mcias/ingestion/parsers/pdf_parser.py uses pypdf to read text per page; scanned pages are quarantined unless optional local tesseract and pymupdf are configured. Image parser invokes optional OCR and quarantines unreadable input. PDF scanned fallback has fixed confidence 0.5.
- Palermo-1 currently checks completeness/quarantine, not medical field precision or invoice arithmetic.
- Neither structured medical entity extraction nor grounded line-item assignment is demonstrated by these source files. The pilot does not modify them.

## Executable preliminary baseline
scripts/document_reader_isolated_pilot.py creates five text-native synthetic English PDF examples: invoice, laboratory, radiology, prescription, mixed. Each has independently saved ground_truth.json with page-1 text evidence; an image-only laboratory PDF probes review routing. It extracts pypdf page text and scores exact-value presence. This IS NOT field-level, reading-order, bounding-box, Arabic, invoice arithmetic, or cross-document benchmark. Generated PDFs are basic preliminary fixtures, not the complete requested benchmark. CI intentionally checks that image-only source is REVIEW rather than guessing.

Workflow: .github/workflows/document-reader-isolated-pilot.yml. Results and PDFs available only after successful workflow; do not claim SUCCESS before actual job verification. No database, network API, or real patient data.

## OCR candidates (NOT BENCHMARKED)
- PaddleOCR / PP-StructureV3: source code Apache-2.0 according to official PaddleOCR repository. Runtime and model weights, CPU memory/performance, and Arabic medical invoices remain to be verified on a pinned install. Project: https://github.com/PaddlePaddle/PaddleOCR
- Surya: upstream code and model-weight terms differ across published versions; recent upstream states code Apache-2.0 while model weights are under a modified OpenRAIL-style license with commercial restrictions. Do NOT presume unconstrained commercial use or download weights without reviewing the exact pinned license. Project: https://github.com/datalab-to/surya
- Neither model installed or measured here; no fabricated OCR comparisons. Heavy dependencies, weights and GPU availability must be established in a later isolated benchmark job.

## Critical acceptance gaps
1. Arabic/right-to-left synthetic fixtures with an available licensed font; complex multi-page invoices and row/column ground truth.
2. Image-only, tilted, noisy scans and real offline OCR evaluation.
3. Reliable structured fields: currency, unit price, qty, total, lab numeric result vs range, drug dose, diagnosis attribution, dates, supporting page/region coordinates.
4. Field-level precision/recall, hallucination, row swaps, cross-document contamination, latency and peak memory for each engine.
5. Untrusted source prompt injection test; default UNRESOLVED/HUMAN_REVIEW, never autonomous clinical/financial judgments.

## Handoff
Do not select OCR engine or integrate into active ingestion until benchmark quality, privacy and license checks pass. No merge, deploy or production DB. Only synthetic isolated comparison.


## Cross-branch read-only reuse assessment (2026-10-20)
Verified PR HEAD snapshots before reuse (not edited):
- PR19 agent architecture: babb9ef175de1135c837c4ea439400b28369c826.
- PR20 A1: b536a94adf4d190ac48856bd435a8a624f3931f4.
- PR22 temporal references: b694a2a1603a9a4c6d7af26ed56035b1a28b0166.
- PR23 contract intelligence: 39a4a9b93e9eb04ea7c09c8c155c3e08f38c6ec0.
- PR25 unified inputs: a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1.

Read docs/agents/A1_DATA_CONTRACT_AR.md, mcias/agents/a1_trusted_input.py, tests/test_a1_itemized_decimal_provenance.py, mcias/agents/invoice_integrity.py, mcias/contract_intelligence.py and tests/test_contract_tariff_segments.py from pinned source refs. This is selective interface/fixture reuse, NOT branch merging.

**Reused:** A1's *actual* pure read-only `analyze` implementation, obtained by a separate SHA-pinned read-only GitHub checkout in isolated CI, alongside an independently generated strict-text Reader fixture and the arithmetic counterexamples (wrong quantity/price and swapped rows). A1's financial findings and Reader extraction findings are reported separately in `reader_a1_bridge_results.json`. Reused contract intelligence's exact-clause/record identity evidence principle and rejection of cross-provider tariff amounts as a benchmark design constraint, not its inference engine or contract authority.

**Not reused:** `a1_trusted_input.py` requires authorized server actor, G2 encrypted originals, SHA256 re-reading and byte/row identity, tenant-scoped G4 data and source locators; none may be fabricated for OCR-derived PDF. Its trusted snapshot cannot be invoked on text-only fixtures. PR22 ReferencePoint is not signed fee authority; PR23 Contract Intelligence provides DRAFT_ONLY suggestions, not A1 tariff authority; PR25 contract/input changes are outside the isolation boundary. No contract, shared audit, G1/L1 or production runtime changes.

**Reader-to-A1 experimental boundary:**
1. Reader outputs item records with per-field value, exact text evidence, page, line and character offset where available, plus uncertainty and parse issues. It MUST NOT produce G2's `original_sha256_verified=True` or `extracted_rows_equal_original=True` based solely on a digest of OCR text.
2. A1's untrusted pure arithmetic preview may accept a synthetic `invoice.items` bundle with `document_id/sha256/locator` where the SHA hashes fixture bytes, but this is a *synthetic source anchor only*, NOT an encrypted-original attestation or production-compatible A1 trusted input.
3. Until independently re-opened original bytes match SHA256 and every extracted field/row and provenance coordinate is reconciled against a verified G2 source with trusted server tenant/access control, the bridge is `HUMAN_REVIEW` and claim/contract/quantity/unit authority is `INSUFFICIENT_EVIDENCE`. No automated financial outcome.
4. A1 pure `analyze` is used only as an advisory rules engine; no G4 preview endpoint, store or database is involved.

**New measurable tests:** `scripts/document_reader_structured_pilot.py` has eight labelled synthetic controlled-English *text* cases with strict row schema, review on swapped amounts and malformed rows, line/page provenance and prompt-injection disregard; script uses `tracemalloc` Python allocations (not true process RSS). `scripts/document_reader_a1_bridge_pilot.py` exercises four synthetic Reader-to-A1 cases, expecting 0/1/2/0 arithmetic findings, always requiring review and withholding totals and claim amount rather than inventing values. Workflow: `.github/workflows/document-reader-structured-isolated.yml`. Results count as successful ONLY after GitHub Actions completes at the actual head SHA.

**Remaining benchmark gaps:** no measured Arabic OCR, PaddleOCR, Surya, handwriting, noisy/tilted scanning, medical semantic generalization, multi-column reading, full document bounding-box localization or sourced G2 PDF-to-A1 trusted snapshot. Do not conflate synthetic rule assertions with OCR engine benchmark. No selection of an OCR engine is yet justified.

## HANDOFF for independent reviewer
Verify both new workflow jobs and inspect generated result artifacts. Check that the SHA-pinned A1 code was loaded unmodified. Do not approve integration until a byte-verified G2 source and independent field/row evidence qualification (including image OCR) passes. No merge, deploy or financial actions.


## Measured offline OCR baseline — GitHub CI evidence 2026-10-20
- Actual local MCIAS Tesseract adapter run, not simulated: [GitHub Actions run #39337544635](https://github.com/overurdream-collab/test2/actions/runs/39337544635) at commit `d73b3f3b0ac839cda7086339c800d227ab466dc7`, three jobs passed (strict structured synthetic text, SHA-pinned PR20 A1 bridge, offline local OCR).
- Dataset: 12 original synthetic PNG renderings, 4 contents (2 English, 2 Arabic), each in clean, 2° tilted and Gaussian-blurred versions. Actual `tesseract-ocr-eng` and `tesseract-ocr-ara` installed in Linux runner. DejaVu system font, PIL, no patients or external OCR service.
- Character error rate method: Levenshtein edit distance after removing Unicode whitespace, measured against fixture text; English mean normalized CER `0.000000` (6 images); Arabic mean normalized CER `0.3242082662` (6 images). These small fixtures are **not** a representative statistical accuracy estimate; the mean has few cases, and reading order/RTL normalization can influence it.
- Time, per-sample outputs, Python process peak RSS and measured CER are saved in the workflow artifact `reader-local-ocr-synthetic` / `offline_ocr_baseline.json`. RSS is process high-water mark, not per-inference incremental memory; no model-specific independent memory comparison.
- PaddleOCR / PP-StructureV3: upstream source Apache-2.0 per official project, but exact model weights and transitive dependencies require pinned-model approval before benchmark. NOT_RUN; no comparative win established.
- Surya: upstream source Apache-2.0; model weights published under separately modified OpenRAIL-style terms with commercial conditions. Exact terms must be approved before downloading/using; NOT_RUN.
- The English/Arabic OCR benchmark measures image transcription only; these pixels have **not** yet passed a full OCR → structured reader → byte-verified G2 → A1 pipeline. The field-level bridge tests only controlled text. A high OCR score cannot attest line-item identity.

**Acceptance decision: PARTIAL — SPECIFIC BENCHMARK GAPS.** Strictly synthetic read-only tests and pinned A1 arithmetic bridge passed; full medical document understanding and independently attested PDF OCR remain unproven. No merge, no deploy, no claim settlement.
