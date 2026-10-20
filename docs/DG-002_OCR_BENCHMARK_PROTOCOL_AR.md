# MCIAS v2.0 — DG-002A — Medical OCR Comparative Benchmark Protocol

**Status:** DG-002A RESEARCH + MEASUREMENT CONTRACT PREPARED; DG-002B / DG-002C **NOT RUN**.  
**Date:** 2026-10-20. **Owner:** existing Document Reader agent, NOT a new agent.  
**Branch:** `feat/mcias-document-reader-isolated-pilot`.  
**Inspected baseline:** `257d58a1619137720e7dd44e7dfb047736a5cb4b`; successful prior isolated PG16/G2/Shared Audit/A1 run: https://github.com/overurdream-collab/test2/actions/runs/39462349692 .  
**Scope:** offline, synthetic, read-only model comparison. NO MERGE / NO DEPLOY / NO PHI / NO TRAINING / NO FINANCIAL AUTHORITY.

## Source-of-truth models (vendor claims are NOT MCIAS metrics)

1. **Current Tesseract:** actual MCIAS local adapter `mcias/ingestion/ocr_engine.py` and reusable `scripts/document_reader_offline_ocr_benchmark.py`, `scripts/document_reader_dynamic_layout_pilot.py`. Existing tiny synthetic baseline: English whitespace-normalized CER 0, Arabic ~0.3242 across six Arabic PNG examples; NOT representative Arabic medical field accuracy. Pin local binary and `ara`/`eng` traineddata file checksums on the new benchmark runner.
2. **PaddleOCR-VL-1.6:** official model `https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6`, **Apache-2.0 model card**, model series ~0.9B, official pipeline `PaddleOCRVL(pipeline_version="v1.6")`; official usage `https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html`. Official 96.33% **OmniDocBench v1.6** is vendor/general benchmark, NEVER label it as Arabic invoice/lab accuracy. Requires explicit PaddlePaddle/PaddleOCR runtime and additional layout engine. Pin model revision/weights SHA, package lock, and memory limits before DG-002B.
3. **DeepSeek-OCR-2:** official `https://huggingface.co/deepseek-ai/DeepSeek-OCR-2`, **Apache-2.0 model card**, ~6.79GB repository/6.78GB safetensors as displayed by Hugging Face on inspection; NVIDIA reference includes `torch==2.6.0`, `transformers==4.46.3`, `flash-attn==2.7.3`, custom `trust_remote_code`. This is *not* a guarantee of safe dependencies/weights or host RAM/VRAM; audit executable model code before loading. Do not install in ordinary Github-hosted CPU CI automatically. DG-002C optional when a suitable preapproved isolated GPU is available. Do not equate disk size with peak VRAM.

## Reuse, no duplication

- Synthetic PNG/Tesseract CER samples from `scripts/document_reader_offline_ocr_benchmark.py`.
- Three scanned, alternate-order English and Arabic RTL invoice fixtures, independent authored gold, field/row IDs and bboxes from `scripts/document_reader_dynamic_layout_pilot.py`.
- Existing scanned PDF, lab/radiology/prescription fixture generators and immutable original SHA provenance. No change to ReaderAgent, G2, A1, Shared Audit, schemas or migration chain.
- Keep evaluation fixtures **frozen** before comparing engines. Derive gold independently of model output; no tweaking labels after model predictions. Model normalization/mapping adapters MUST never read gold at inference time.

## Staged dataset and evaluation protocol

**Stage 0:** tiny smoke with exact same 3 existing layouts and 12 PNG examples; validate install, reproducible deterministic outputs and time/RSS/VRAM. Mark insufficient external validity.

**Stage 1:** prepare additional independent synthetic templates: invoices EN/AR (RTL and mixed numbers), laboratory reports (result/reference/unit), prescriptions (drug/strength/dose/frequency/duration), radiology reports (body/site/impression), medical notes, multi-page scans, skew/blur, and confusing headers. Separate generator/template families in DEVELOPMENT and LOCKED EVALUATION folds; publish synthetic gold and stable PDF/PNG SHA manifests. Avoid overlapping fonts/layouts as the sole holdout difference.

**Stage 2 (later, separately authorized):** independently reviewed consented/de-identified real-world set with institution permission, independent medical/billing experts, privacy constraints and licensing; no claims of production accuracy without it.

## Prediction schema for DG-002 scoring

Provide `--gold gold.json --prediction model.json --output report.json` to `scripts/document_reader_dg002_score.py`.

Both JSONs: `{"documents":[{"id":"synthetic-1","sha256":"<64hex>","language":"ar","pages":[{"page":1,"text":"raw recognized text"}],"fields":[{"field_id":"item-1.price","kind":"amount","value":"30.00","page":1,"row_id":"item-1","bbox":[100,20,160,50],"review_required":false}]}]}`. Prediction should also report engine metadata: `engine`, `runtime_seconds`, `peak_rss_mb`, `peak_vram_mb` measured by the runner. Missing measurements remain null/NOT_MEASURED, not zero. A `sha256` mismatch is a fatal source-integrity gate. OCR confidence is uncalibrated unless separately calibrated on holdout.

**Primary patient-safety measurements:**
- exact medically meaningful field value (NFC + boundary whitespace only; do not silently convert Arabic digits, doses, decimals or medication names);
- source row, correct page, IoU≥0.50 per field box; report value and evidence association separately;
- unsafe accepted wrong critical fields vs explicit HUMAN_REVIEW/abstentions (do not reward universal abstention);
- by-language and by-field-type precision, recall, errors and false invented fields;
- CER (whitespace-insensitive) and WER (tokenized), correctly attributed to same source pages;
- model startup/warm/cold latency, pages/s, peak process RAM, peak GPU VRAM and hardware SKU.

**Forbidden score inflation:** Do not count unmatched gold fields as correct. Do not use synthetic gold to auto-approve OCR in G2 or manufacture `extracted_rows_equal_original=True`. Do not count a model output value as correctly linked if the bbox belongs to a different row/page even if text matches. Do not compare vendor published OmniDocBench scores with measured MCIAS CER. Never hide hallucinations, source mismatches, review holds or unsuccessful model startups.

## Gate design

- DG-002A PASS only when official models/licenses, dependency risks, reuse plan, scoring schema and independent unit test on scorer are recorded. It is **not** model benchmarking.
- DG-002B PASS requires **both engines actually executed** on *identical* SHA-matched synthetic inputs, labeled splits and environment/hardware metadata, with raw outputs saved. A first smoke may remain PARTIAL pending resources.
- DG-002C is optional; if DeepSeek cannot run locally, record `NOT_RUN_RESOURCE_LIMIT`, never a fabricated metric or comparative rank.
- Any accuracy/regression winner is **recommendation for isolated trials only**; no OCR swap, G2 trust promotion, auto patient medical inference, financial decision, or training authorization.

## Owner/hand-off

Document Reader owns only DG-002 benchmark scripts, synthetic fixtures and report. Contract Intelligence owns C34 on PR23; W1 owns its existing branch; Alembic architect writes read-only design; A1/Shared Audit/PR25 remain read-only dependencies. PR #20 trusted adapter does not accept OCR/PDF by default.

**NEXT:** Implement the frozen manifest and model adapters on a separate DG-002B scope, run Tesseract and PaddleOCR-VL-1.6 on the same assets only when runtime is actually available, then compare field-level outcomes. Record exact GitHub SHA and CI; documentation-only code smoke does not certify a model.
