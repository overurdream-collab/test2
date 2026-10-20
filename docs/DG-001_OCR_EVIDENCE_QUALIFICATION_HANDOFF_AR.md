# DG-001 — G2 OCR Evidence Qualification (isolated synthetic pilot)

**Decision boundary: OCR CANDIDATES FOR HUMAN REVIEW ONLY — NO TRUSTED A1 INPUT.**
The prior Dynamic Layout and G2 AES-GCM source custody pilots are closed; this pilot reuses their synthetic invoice generator, actual G2 ingestion and original-byte reopening, without modifying either original implementation.

## Executable evidence

- Script: `scripts/g2_ocr_evidence_qualification_pilot.py`.
- CI: `.github/workflows/g2-ocr-evidence-qualification.yml`.
- 3 synthetic image-only PDF documents, 3 rows × 6 fields = **54 unverified OCR field candidates**. Local in-memory SQLite table `reader_ocr_candidate_isolated` is defined **only in the test script** and is not a production G2 schema migration.
- Each candidate persists organization ID, actual G2 `IngestionDocument` ID, `IngestionJob` ID, original PDF SHA-256, page number, row ID, field name, observed text, OCR word evidence, pixel bbox, uncalibrated OCR confidence, and status `UNVERIFIED_OCR_CANDIDATE`.
- Re-opens the real source bytes from the native AES-GCM store before independently rerunning OCR. Compares stored observations with the reopened raster, OCR words, authored synthetic ground-truth row identity and cell placement. OCR repetition is not an independent image-understanding model: the separately authored synthetic gold is only a **test oracle**, not a trusted clinical source.
- Strict gates: 18/18 correctly sourced field values and 18/18 correct cell regions per synthetic PDF; unverified candidate status remains unchanged; no `ExtractedSourceRecord` inserted; G2 documents remain `review_required`. Pure A1 analyzer is only an optional advisory preview when source and mandatory metadata are complete. The Arabic unknown date blocks A1.
- Seven negative checks: absent price candidate, amount moved to another row's visual cell, changed quantity, attempt to mark OCR evidence TRUSTED, wrong organization, wrong original digest, and damaged encrypted original (AES-GCM tag rejection). All must block candidate qualification for preview or source reopening.
- Exact PR20 A1 pinned commit: `b536a94adf4d190ac48856bd435a8a624f3931f4`. CI separately verifies the **actual trusted A1 adapter** rejects a `review_required` scanned PDF, and that `SourceVerification` refuses unverified original or row attestations.

## Trust boundaries and gaps

1. Original PDF bytes: verified by actual native G2 store retrieval and SHA-256 under a synthetic tenant; this alone never attests the OCR interpretation.
2. OCR candidate evidence: persisted as untrusted test rows, cross-checked against synthetic gold and source pixels; **not promoted** to native G2 trusted source records. The original G2 job remains quarantined/review-required.
3. A1: the pinned pure `analyze` function is used for diagnostic arithmetic only; the trusted A1 source adapter for CSV/XLSX **does not support this OCR/PDF evidence**. `original_sha256_verified=True` and `extracted_rows_equal_original=True` must not be asserted to satisfy it without actual supported evidence.
4. No clinical inference, real patient or hospital data, production DB, external OCR service, financial settlement, deployment, merge or modifications of the other PR branches. The next work item requires a separately approved G2-approved OCR provenance contract and human attestation path, not unilateral promotion of OCR rows.

**Handoff: ISOLATED OCR EVIDENCE QUALIFICATION UNDER REVIEW; NO INTEGRATION.** Verify the latest HEAD and actual workflow status/artefact before accepting this phase.
