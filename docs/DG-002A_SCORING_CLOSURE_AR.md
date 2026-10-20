# MCIAS v2.0 — DG-002A Closure — Medical OCR Scoring & Model Research

**Decision:** DG-002A SCORER/PROTOCOL VERIFIED — NOT MODEL ACCURACY ACCEPTANCE.
**Date:** 2026-10-20. **Scope:** Existing Document Reader only; synthetic isolated benchmark.

## Source inspection & pinned baseline

- Verified prior HEAD: `62f733a9e9ad7f5ba6e83c35c1aff6836f972fbe`.
- `docs/DG-002_OCR_BENCHMARK_PROTOCOL_AR.md` inspected without changing its medical precision/evidence/source semantics.
- `scripts/document_reader_dg002_score.py` and its **9 existing unit tests** pass in GitHub Actions [#39477585681](https://github.com/overurdream-collab/test2/actions/runs/39477585681) on the exact baseline SHA.
- The scorer uses exact NFC-preserved medical values, page/row/bbox IoU >=0.50, per-kind and per-language counts, CER/WER, SHA-256 mismatch rejection, abstentions, invented field IDs, and unsafe accepted fields. The scorer and nine tests are **unchanged**; no verified scorer defect demanded altering them.
- Detected and corrected a genuine **DG-002B adapter** bug independently: Arabic TSV words were previously reassembled left-to-right. They are now ordered right-to-left inside the detected value region; invisible directional LRM/RLM characters are removed at OCR token ingress, not from gold. Measured Arabic exact values improved 1/15 -> 8/15 on the *same frozen synthetic oracle*. This does **not** prove the Arabic OCR engine improved.

## Exact engines / license / resource investigation

- Tesseract 5.3.4 with installed `eng` / `ara` traineddata: actually executed in DG-002B; not a medical-grade OCR certification.
- PaddleOCR-VL-1.6 model: `PaddlePaddle/PaddleOCR-VL-1.6`, Apache-2.0 model card; frozen Hugging Face model revision `676e2aad67375fec9c7dcc9740babec7a0d0d110`. Official pipeline is `PaddleOCRVL(pipeline_version="v1.6")`, with separate PaddlePaddle, PaddleOCR and layout dependencies. Official documentation explicitly permits x64 CPU mode; no GPU is not proof of incompatibility. Vendor OmniDocBench metrics are **not** MCIAS metrics.
- DeepSeek-OCR-2 official `deepseek-ai/DeepSeek-OCR-2`, Apache-2.0 card, about 6.79GB repository (6.78GB safetensors), with repository-executable model code and possible `trust_remote_code`. **NOT_RUN_RESOURCE_AND_CODE_REVIEW_GATE**; no cost incurred or comparative claims.

## Scope & next step

Proceed only with fixed synthetic medical invoice, laboratory, radiology and prescription PNG/PDF files in Arabic/English; save authored Gold, raw Predictions, source-bbox/row association metrics and all unresolved cases. Never promote OCR to authenticated G2 rows, medical diagnosis, A1 trusted PDF input, or a financial decision. **NO MERGE — NO DEPLOY — NO PATIENT DATA.**
