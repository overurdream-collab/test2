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
