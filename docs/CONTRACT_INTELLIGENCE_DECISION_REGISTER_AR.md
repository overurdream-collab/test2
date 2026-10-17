# Contract Intelligence — سجل القرارات

## CID-001 — 2026-10-17 — RESEARCHED / pending real benchmark
Decision: Keep existing MCIAS G2/pypdf/openpyxl/Tesseract as default; don't install Docling/MinerU/Marker just because popular. Rationale: source encryption, tenant isolation, quarantine, typed record locators already exist; replacing breaks proven invariants. Alternatives evaluated: Docling MIT, MinerU custom license, PaddleOCR Apache, Unstructured Apache, Marker code Apache+weights restricted, OCRmyPDF MPL. Risks: loss of table layout and Arabic OCR unreliability. Next: native vs Docling/Paddle benchmark with gold synthetic corpus.
## CID-002 — 2026-10-17 — CANDIDATE / NOT VERIFIED
Decision: Qwen3-4B-Instruct-2507 Apache-2.0 first model *candidate* for bounded structured JSON on local inference, with Qwen3-VL only for image complexity. No inference has run. No external PHI; a local model runtime must be configured and tested, do not assume Gateway exists.
## CID-003 — 2026-10-17 — BINDING SAFETY
AI gives citations/typed proposals only, never active financial instructions. Evidence resolver rechecks exact quote against original extracted record, page/row, tenant; uncertain/missing dates or mismatched OCR numeric values demand human review. No eval/exec/LLM SQL. Typed compiler diagnostic only before institutional signature; G3/G5 unchanged. See DG-001 / PR #22.
## CID-004 — 2026-10-17 — DATA CONTRACT
Use existing ReferencePoint/Closure after human promotion; before that store draft-only candidate records scoped org/document/job. If additive table necessary use Alembic new revision (0020+) and do not alter 0019. No deletions of historical source, point or closure. All prices isolated by provider/service/currency/effective date.


## CID-005 — C8 constrained pretrained CPU evaluation (PENDING_CI)
Decision: Test official `Qwen/Qwen3-0.6B` Apache-2.0 revision `c1899de289a04d12100db370d81485cdf75e47ca` on 4 synthetic Arabic/English/mixed/injection text cases in free standard public GitHub Actions, local loopback only. This is not final model selection: 0.6B is a resource-compatible feasibility baseline compared with earlier Qwen3-4B candidate, not proven accurate. Do not export real contracts. Record actual model output hashes and TP/FP/FN via `scripts/contract_ai_benchmark.py`, never fabricate success. If dependency downloads fail, status BLOCKED and investigate smaller legally licensed model or a private approved runner; no money spent. Need larger 20+ synthetic fixtures and OCR gold for final selection.


## CID-006 — 2026-10-17 — REUSE existing JSON grammar validator (experiment only)
Observed C9 true Qwen3-0.6B output: fenced top-level JSON arrays, wrong keys/enum, and misleading injection content; four attempts yielded no accepted clauses. The OpenAI-compatible toy local CPU benchmark did not actually implement the `response_format: json_object` contract sent by `infer_local`. Research official https://github.com/noamgat/lm-format-enforcer at v0.11.2 (2025-08-09), repository MIT license, actual Transformers prefix-tokens integration and tests, remaining open issues (format parser edge cases). **Decision:** reuse `lm-format-enforcer==0.11.2` in isolated synthetic CI benchmarking instead of coding a homegrown JSON parser or relaxing numeric/source evidence. Whitelist schema includes all section types and optional values, not gold answers. No production dependency chosen; tool's format guarantee does NOT validate semantic truth. Benchmark must measure independent quote/locator validation and reject injected instructions as source text. If constrained run fails, record as actual FAIL, do not count JSON validity as acceptable contractual extraction.


## CID-006 — 2026-10-17 — MODEL COMPARISON EXPERIMENT (NOT SELECTED)
- At C11 SHA bee37b2df08f827c4e9fe53af604c064f8c0c808 the pinned real Qwen3-0.6B emitted four syntactically valid empty arrays with lm-format-enforcer; source-verified recall remained zero. Run a legally reusable stronger official candidate Qwen/Qwen3-1.7B (Apache-2.0; Hugging Face official snapshot revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e) under identical SYN gold and validators on free CPU CI. No default production model change. Model weights ~4GB and CPU memory/performance are unverified; abort with honest FAIL on memory/runtime/zero recall. A successful 4-case test alone is insufficient to select a model or certify Arabic OCR.


## CID-007 — 2026-10-17 — EXPERIMENT: force candidate in test harness only
- The optional-empty JSON grammar produced only `{"clauses":[]}` on both Qwen3-0.6B and Qwen3-1.7B when reading three verifiable SYN examples. For diagnosis only, require at least one candidate for ALL sources including the negative injection, without conditional use of known gold labels. Evaluate model capacity to fill the 11 typed fields; count quarantined candidates and fail if any negative is incorrectly source-verified. This DOES NOT authorize forcing candidates in institutional production, relaxing G2 quotes, or generating executable finance rules.
- Test result remains PENDING on C14 SHA; compare to pinned historical model runs, then decide suitable real-model serving pipeline with larger corpus. Binding safety CID-003 remains unchanged.


## CID-008 — 2026-10-17 — Binding fail-closed effective date provenance
- ISO date syntax and existence somewhere on the PDF page are insufficient proof of an individual clause's temporal validity. For PDF/image require date in the exact quoted passage; for Excel table allow same row separate cell; inferred/cross-paragraph date gets needs_human_review. It is intentionally conservative and may block valid header-based dates until an independently reviewed reference relationship is implemented. No AI discretion to choose another period; G3/G5 historical financial authority untouched. C15 tests and CI PENDING.


## CID-009 — 2026-10-17 — Exclude literal contract identities in system prompt
- Real pretrained Qwen3-1.7B copied the exact fixed tutorial `P7:XRAY` key and USD/1200 context even while quoting unrelated H1 CONSULT, Arabic copay and malicious text (C14 run 39065549717). Decision: keep system prompt schema-only with no sample provider, service, amount, currency or date; separate source text in user role; retain independent source/date/tenant/typed guards and no automatic finance execution. Do not consider nonempty JSON proof of factual extraction. C16 exact-sha tests PENDING.

## CID-010 — 2026-10-17 — Quote-scoped financial identifiers, not page-scoped
- A PDF page may list H1 and H2 with identical price or multiple services/currencies. Model candidates must not verify merely because a proposed provider_code/service_code/currency exists somewhere on the same PDF page. Require presence within the same exact quote for PDF/image; XLSX identifiers must remain in the same G2 row. Ambiguous references to header/provider require human adjudication, not programmatic guessing. No G3/G5 tariff change. New C19 CI PENDING.

## CID-011 — 2026-10-17 — Qwen2.5-1.5B-Instruct MODEL TEST ONLY
- Compare official open licensed Qwen2.5-1.5B-Instruct SHA 989aa7980e4cf806f80c7fef2b1adb7bc71aa306 (Apache-2.0, 3.09GB) after Qwen3 small models failed to extract typed fields. Same frozen four SYN snippets and independent G2 evidence guard. New inference test PENDING; no claim or default model until 20+ file benchmark, actual Arabic OCR and human review. Model license/source official Hugging Face repo. No private data to hosted runner.
