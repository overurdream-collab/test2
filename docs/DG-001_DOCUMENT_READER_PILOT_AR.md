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


## Phase 2 — Single connected image-only PDF → OCR → A1 experiment (2026-10-20)

**Boundary/acceptance: isolated technical pilot ONLY; no merge, deploy, G2 write or claim processing.** Independent review retained PILOT PARTIALLY ACCEPTED — NO INTEGRATION. No patient records.

### New implementation
- \`scripts/document_reader_scanned_pdf_a1_e2e.py\`, executed through \`.github/workflows/document-reader-structured-isolated.yml\` / job \`scanned-pdf-e2e-quality-gate\`.
- Reproducibly creates **three** distinct two-page synthetic PDF invoices, with *image-only pages* (no selectable PDF text). A multi-column table includes line ID, code, explicitly printed **unit**, quantity, unit price and line total. Repeats invoice headers and includes a printed malicious instruction which is ignored as untrusted document content.
- Cases: valid three-line invoice (30.00 + 45.00 + 21.00 = 96.00 USD), swapped 45.00/30.00 line totals with preserved 96.00 stated invoice total, and a missing unit-price cell. Only fixture authored ground truth contains expected values; OCR parses rendered page pixels independently using actual local Tesseract TSV, not strings from ground truth.
- Reopens the original PDF bytes and computes SHA-256. A tamper regression changes the file's bytes and proves that the original expected SHA is rejected before parsing. Each OCR cell has page, pixel bbox, OCR text, and engine-reported **uncalibrated** confidence; no confidence is hard-coded at 1.0. A1 row references use the **union of all OCR field bounding boxes** in that row. Each individual field retains its own OCR word boxes.
- The read-only cross-branch A1 function is checked out from **exact SHA** \`b536a94adf4d190ac48856bd435a8a624f3931f4\`; the checkout is verified, code unchanged, and no other PR is modified. A1 sees only explicit OCR-derived unit/code/quantities/prices/totals; no invented unit, tariffs, claim amount or attested performed quantity.
- No call to \`mcias/agents/a1_trusted_input.py\`: its authorization, encrypted G2 original source verification and row equality **cannot** be claimed by a local PDF byte hash. Every review packet says \`g2_original_verified=false\`, \`g2_rows_verified=false\`, \`financial_decision=NOT_AUTHORIZED\` and \`review_outcome=HUMAN_REVIEW\`. The G4 claim and contract authorities remain intentionally unavailable.

### Independent stage scoring and hard quality gate
- **Reader stage**: per-case actual OCR outputs, expected vs read fields (invoice metadata and line items), exact-value recall, correct-cell/page bounding-box localization, unresolved field reasons and OCR elapsed seconds. A template-based detector crops predefined cells; therefore perfect fixture results **cannot** be generalized to arbitrary invoices or Arabic layouts.
- **A1 stage**: independently asserts 0 expected line-arithmetic findings for valid lines and 2 for the deliberately interchanged line totals, even while the invoice-wide sum matches. When one price is blank, A1 is **not** called, \`INSUFFICIENT_EVIDENCE\` is reported, and the source is retained for HUMAN_REVIEW.
- **Security stage**: altered PDF bytes trigger SHA256 mismatch; malicious written instructions cannot invoke decisions because OCR output is treated only as data, and no LLM or action executor is used.
- **CI pass condition**: not just successful OCR invocation; exact match of all critical fields and correct visual cell assignment, expected A1 arithmetic counts, no unsupported price filling, no financial decision, and negative source tamper test.
- For this **updated fixture with explicit unit cells**, 23 critical fields and 18 row-field visual evidence coordinates are expected per complete invoice. The resulting GitHub workflow artifact \`reader-scanned-pdf-e2e-evidence\` includes the PDFs, independently generated gold labels, per-case review packets, and \`summary.json\`. Verify this updated job on the **latest** SHA, not earlier green runs.

### PaddleOCR comparison decision
- Official code: https://github.com/PaddlePaddle/PaddleOCR (Apache-2.0). The specific lightweight recognition weights candidate \`PaddlePaddle/en_PP-OCRv5_mobile_rec\` lists Apache-2.0: https://huggingface.co/PaddlePaddle/en_PP-OCRv5_mobile_rec . However the official runtime requires PaddlePaddle 3.x plus supported model artifacts/dependencies: https://www.paddleocr.ai/main/en/quick_start.html .
- This phase does **not** install or measure PaddleOCR. The model, exact revision, cryptographic weight checksum, inference runtime and transitive dependency conditions have not been pinned and qualified in the isolation job. Comparing absent PaddleOCR numbers with measured Tesseract would be dishonest. **Comparison remains NOT_RUN**, not failed accuracy. No claim that resource exhaustion has been proven.
- Surya remains NOT_RUN pending exact weight license/commercial-term qualification.

### Handoff / acceptance limits
The new chain is **synthetic template-constrained**, actual scanned-PDF OCR and A1 advisory arithmetic, not a generic reader or G2 trusted-source integration. A local PDF hash verifies local bytes only; neither original encrypted G2 custody nor independent G2 row equality is proven. The real-world hardest cases (Arabic itemized PDF, mixed orientations, unstructured tables, page-order collisions, contracts and clinical assertions) remain UNPROVEN. **Decision: PILOT PARTIALLY ACCEPTED — NO INTEGRATION.**
