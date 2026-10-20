# DG-001 — G2 synthetic custody handoff

Status: PARTIAL; no integration, merge or deployment.

## Verified components

- Native `mcias.storage.EncryptedStore` and `mcias.ingestion.orchestrator.ingest` used unchanged.
- Offline synthetic SQLite, isolated temporary AES-GCM key and fictional organizations.
- Actual SHA-256 verification occurs after reopening the encrypted PDF.
- A1 uses its pinned unchanged pure `analyze` function and returns advisory review only.

## Results and safety boundary

- Run #39345192503: SUCCESS on SHA `800e233978e74ef92ee57c0605a49749d599f31d`; 3 synthetic PDF originals reopened from G2 and 6 negative tenant/digest tests passed.
- Both completed English invoice variants meet 18/18 authored value and 18/18 authored cell-location checks; original pinned A1 reports 0 and 2 arithmetic findings. Arabic date uncertainty blocks A1.
- G2 intentionally marks scanned PDFs `review_required` when local ingestion OCR is disabled. It produces **zero trusted cell-level `ExtractedSourceRecord` rows** in this test.

## Independent review handoff

Encrypted source custody and byte identity are **verified for synthetic documents only**. Independently authored synthetic ground truth is NOT a substitute for a G2 signed or otherwise trusted original cell-row representation. Never assert `extracted_rows_equal_original=True` for OCR, never call the `a1_trusted_input` adapter, never persist payment authority, and retain `HUMAN_REVIEW` and `financial_decision=NOT_AUTHORIZED`. The next unresolved engineering gate is safe cell-level original-image reconciliation under G2 governance, not a new OCR benchmark. **NO MERGE / NO DEPLOY / SYNTHETIC DATA ONLY.**
