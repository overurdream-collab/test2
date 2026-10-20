# MCIAS v2.0 — DG-002B Medical OCR Comparative Pilot — FINAL REPORT / HANDOFF

**Decision: PARTIAL — SPECIFIC GAPS.** Date 2026-10-20. Owner: existing Document Reader. No ReaderAgent replacement. **NO MERGE / NO DEPLOY / NO PATIENT DATA / NO FINANCIAL DECISION.**

## 1. Source and verified CI

- DG-002A verified baseline `62f733a9e9ad7f5ba6e83c35c1aff6836f972fbe`: original scoring script and all **9** tests passed [#39477585681](https://github.com/overurdream-collab/test2/actions/runs/39477585681). Separate closure: `docs/DG-002A_SCORING_CLOSURE_AR.md`. DG-002 scorer was not modified.
- Actual Tesseract DG-002B on `55a7f382d0e3b2c0147900fadad1ad3e186cb7c2`: [#39481716246 — SUCCESS](https://github.com/overurdream-collab/test2/actions/runs/39481716246); evidence Artifact `reader-dg002b-medical-ocr-gold-predictions-metrics`. Runs source code from `scripts/document_reader_dg002b_benchmark.py`. It includes eight stable PNG/PDF assets, independent authored `gold.json`, `manifest.json` with image/PDF SHA-256, `predictions_tesseract.json`, `raw_tesseract.json`, `metrics_tesseract.json` and `error_analysis.json`.
- PaddleCPU pinned native model install/inference attempts [#39481443230](https://github.com/overurdream-collab/test2/actions/runs/39481443230) and [#39481903613](https://github.com/overurdream-collab/test2/actions/runs/39481903613). Green GitHub job means evidence saved, **NOT that full Paddle benchmark passed**. The first initialization was blocked by omitted `inference.yml`, the smallest fix added `*.yml/*.yaml`; no third model acquisition was attempted.
- Offline SHA-matched scoring of the **one actually completed** Paddle invoice (no second model load) [#39483963140 — SUCCESS](https://github.com/overurdream-collab/test2/actions/runs/39483963140). The original raw output was copied in limited lossless text/bbox form to `docs/dg002b_paddle_cpu_one_sample.json`, retaining a link to its unmodified full artifact. Output `paddle_partial_prediction.json`, `paddle_partial_metrics.json` in Artifact `reader-dg002b-paddle-actual-one-image-partial-metrics`.

## 2. Corpus, reproducibility and scope

Four types in **both** English and Arabic: itemized medical invoice, laboratory test/result/reference range, radiology site/finding/modality, and prescription medicine/strength/dose/frequency — 8 **synthetic image-only PDFs** and their PNG images, with 30 critical value fields (15 EN, 15 AR). The label tokens are English even for the Arabic-value fixtures; this is a *mixed-language simplified sample*, **not** an Arabic-only clinical layout or unstructured hospital invoice. No skew/blur or handwriting added to this DG-002B stage. Image and PDF byte hashes are independently recorded in the manifest. Gold is generated separately from OCR in deterministic fixture code and is never an inference input.

The same Gold and Manifest were confirmed **byte-for-byte identical** before and after the Arabic RTL adapter correction. The change only orders recognized Arabic value tokens from right to left and strips nonsemantic LRM/RLM from OCR output: measured Arabic exact match improves **1/15 → 8/15**. Neither the frozen gold nor the DG-002A evaluator was adjusted to fit OCR predictions.

## 3. Real measured outcomes (not vendor benchmarks)

| Measurement | Tesseract 5.3.4 CPU: all 8 documents | PaddleOCR-VL-1.6 CPU: 1/8 invoice only |
|---|---:|---:|
| Images processed | 8/8 | 1/8 (remaining 7 NOT_RUN_TIMEOUT) |
| Exact medically relevant values | 23/30 | 4/4 on **English invoice only**, no full-set rate |
| EN values | 15/15 | 4/4 on invoice; other categories NOT_RUN |
| AR values | 8/15 | NOT_RUN |
| Exact values **and field source region** | 22/30 | 0/4 — model emitted whole-page box, not field boxes |
| Correct field source page/row/IoU >=0.50 | 26/30 | 0/4, field locations UNQUALIFIED |
| CER EN | 0.0% on 4 English documents | 0.0% on 1 English invoice |
| CER AR mixed | **30.566%** on 4 Arabic-value documents | NOT_RUN |
| WER EN | 0.0% | 0.0% on one invoice |
| WER AR mixed | **60.0%** | NOT_RUN |
| Tesseract CER/WER overall | 15.197% / 30.3371% | NOT_COMPARABLE |
| Measured inference runtime | **4.007 sec total** for 8 pages | **376.992 sec** for the one completed invoice (no throughput generalization) |
| RAM | about **49.934 MB** maximum observed self/child RSS; not aggregate memory | **NOT_MEASURED** for actual complete inference; trial stopped before final memory summary |
| GPU peak | N/A, CPU | N/A, CPU |
| Unverified fields held for HUMAN_REVIEW | 30/30 | 4/4 |

Field-level source agreement is kept separate from recognition. Paddle inference with `use_layout_detection=False` returns one `[0,0,1280,1040]` OCR block covering the entire page, **not the per-field evidence demanded by DG-002**. The sample equality of text does not qualify it for G2 evidence or medical/financial use.

Tesseract false accepted critical fields: 0 because **all** OCR fields were held for human review. It would be misleading to describe that as automatic safety or high OCR precision.

## 4. Arabic medical errors (preserve original strings)

- Arabic invoice: quantity `٢` → `y`; unit price `١٥٫٠٠` → `0ر10`; line total `٣٠٫٠٠` → `ارس`. Strong financial risk; no automatic claim arithmetic from this OCR.
- Arabic lab result `١٣٫٥` → `10`, and reference range `١٢-١٦` → `11-17`. Clinical interpretation is unsafe without human verification.
- Arabic prescription strength `٥٠٠ ملغ` → `0°: ilo` and frequency `مرتان يوميا` → `po Uli يوميا`. Medication strength/frequency MUST remain HUMAN_REVIEW.
- Arabic radiology words became correct after restoring RTL order. The fix was in the **benchmark tokenizer**, not proof of any improvement in Tesseract's trained model.
- Error type split: **4 reading-only**, **3 simultaneous reading+source association**, and **1 source association-only** (correct English invoice quantity but bbox IoU below 0.5). 30 fields total, 22 correct value+source.

The CER/WER denominator includes English form labels in Arabic-value documents, so Arabic-script-only CER cannot be inferred from these rates.

## 5. Paddle, resources and exact model provenance

Official model ID `PaddlePaddle/PaddleOCR-VL-1.6` (Apache-2.0 model card); pinned HF revision `676e2aad67375fec9c7dcc9740babec7a0d0d110`. **Actually downloaded** `model.safetensors` 1,917,255,968 bytes and verified SHA-256 `85a479d506a11e724e7285d395c551be69f41dbc16b6342d3cacfb189aed71db`. Runtime pinned: `paddlepaddle==3.2.1`, `paddleocr[doc-parser]==3.7.0`, `huggingface-hub==0.36.0`. GitHub runner: Ubuntu CPU, no GPU, ~15.6 GiB total RAM and >80 GiB free disk during preflight.

The first run revealed omitted `inference.yml` and did not infer. After correcting metadata inclusion, the second and **final bounded** attempt initialized the model, ran an English invoice for **376.992 sec**, then exceeded the total trial timeout while attempting more images. It generated neither Arabic results nor individual field bboxes. This is an **engineering time/resource and evidence-linking limitation**, not a measured Arabic model error. No further model downloads were initiated. Full raw original in [Run #39481903613](https://github.com/overurdream-collab/test2/actions/runs/39481903613) Artifact.

Paddle model/source files can require native PaddleX-specific metadata, runtime and region detector. A future GPU/CPU run must pin and verify **all** required layout models and produce independently checkable cell bboxes before a valid comparison. No claim of 96.33% (vendor OmniDocBench) as an MCIAS result.

## 6. DG-002C DeepSeek-OCR-2 research only

Official DeepSeek-OCR-2 Hugging Face model card lists Apache-2.0 and ~6.79 GB repository with ~6.78 GB safetensors, executable remote model code/trust boundary. No verified preapproved free isolated GPU, model-code security review or model download. Status: **NOT_RUN_RESOURCE_AND_SECURITY_GATE**; no accuracy, latency or memory score is available. Do not rank it against measured MCIAS results.

## 7. Recommendation, unresolved gaps and stopping condition

**Retain the existing ReaderAgent and local Tesseract as limited synthetic baseline, not as an approved Arabic medical reader.** The very high numeric/medication error rate in Arabic prevents automatic clinical/billing extraction. PaddleOCR-VL-1.6 is an **unqualified research candidate**, not a proven winner. Next independent benchmark approval should use a reproducible cached GPU/runtime, pinned Paddle native/layout weights, true field-region evidence extraction and all eight identical image SHA inputs. DeepSeek-OCR-2 should remain DG-002C optional until safe free resources and code review.

**Decision: DG-002A CONTRACT VERIFIED; DG-002B PARTIAL — 8/8 Tesseract, only 1/8 Paddle with no qualified cell-level evidence; DG-002C NOT_RUN.** No OCR engine switch, G2 trust elevation, A1 change, Shared Audit change, deployment, merge, production migrations, real patient input or financial decision.

## 8. Resume verification — 2026-10-20 (no repeated inference)

- Latest branch HEAD at resume: `36e03751d71306f33ee50ce4e0dea879e2a4b3c2`. Inspected the actual branch tree and current DG-002A/DG-002B files before writing this note. Existing report, one-sample Paddle snapshot, offline scorer and workflows are present; no reset or duplicate script was created.
- Latest exact-SHA synthetic OCR CI: [#39484279827](https://github.com/overurdream-collab/test2/actions/runs/39484279827), completed **success** on `36e03751`. This verifies the final documented state for the benchmark workflow, **not** a successful eight-image Paddle run.
- Separate no-weights offline Paddle one-sample score: [#39483963140](https://github.com/overurdream-collab/test2/actions/runs/39483963140), completed **success** on `d8637b2b18e7e7ba81f13ee5e25b6f440c92d066`. The one-image source record is `docs/dg002b_paddle_cpu_one_sample.json` and has no field-level bounding boxes.
- Outstanding: Paddle 7/8 not inferred; no qualified field/cell source evidence for its completed invoice; no full Arabic Paddle CER/WER or critical-field score; DeepSeek-OCR-2 not run; limited synthetic layouts without real-world diversity. These are **gaps, not passed tests**.
- Next safe technical step requires separate approval/resources: cached free runtime for all eight same-hash images, verified layout/cell region binding, and medical Arabic error validation. Do **not** rerun 1.92GB downloads or production workflows merely to update documentation.
- This resume only updates this DG-002B handoff. No G2, A1, Shared Audit, ReaderAgent production implementation, deployment or merge.
