# Contract Intelligence — تقرير الاختبار الإثباتي

**الحالة: البحث R0 فقط — NOT COMPLETED.** لا تُحَوِّل نجاح pipeline native إلى ادعاء نجاح وكيل AI.
| Case | Evidence | Result |
|---|---|---|
| GitHub PR state | PR #22 open draft at b694a2a1603a9a4c6d7af26ed56035b1a28b0166؛ PR #19 open draft | VERIFIED metadata |
| Native PDF 2 pages | python /mnt/data/ci_research_tests/probe.py, ReportLab synthetic text, pypdf strict | PASS local smoke (2 anchor facts, **not** accuracy metric) |
| Synthetic English OCR image | tesseract -l eng returned CONSULT H1 5000 YER, return code 0 | PASS local smoke only |
| Synthetic workbook | artifact_tool generated XLSX for H1/H2/H3 size 3475 bytes | PASS file creation; parser NOT_RUN |
| Arabic OCR + mixed PDF, tables, six projects integration | packages/download unavailable and no canonical fixtures copied into repo | NOT_RUN |
| Qwen3 real inference | no locally installed model/runtime or approved GPU, no Hugging Face download from sandbox | NOT_RUN / BLOCKED |
| 20 acceptance scenarios + security/PG/API/browser | Contract Intelligence feature not written at R0 | NOT_RUN |
| Precision/Recall/FPR/FNR | Gold set + predictions absent | NOT_MEASURED |
| CI at research commit | must query Actions on exact HEAD after commit | PENDING_CI |

## Mandatory next reproducible steps
1. Build privacy-safe committed SYN contract fixture generator (Arabic shaped + text PDF + scanned + multilingual + XLSX); run tests on actual repo/CI.
2. Use isolated dependency profile to evaluate Docling CPU and existing pypdf; include license/model revision and page/table row offsets.
3. Launch approved *local* OpenAI-compatible Qwen runtime (Ollama/vLLM optional), record model SHA and actual response without PHI.
4. Compute TP/FP/FN per clause on frozen gold annotations; Precision=TP/(TP+FP), Recall=TP/(TP+FN), FPR on defined negatives, no estimated success percentages.
5. GitHub Actions on exact branch HEAD for G1–G9, governance, integration and browser, attach URLs/status. Independent review before merge.

## C1 evidence gate
New tests/test_contract_intelligence.py introduces synthetic tests for quote, row, source hash, typed Decimal, duplicate and conflicting clauses, missing dates, prompt injection, endpoint SSRF and model unavailable. **No PASS attributed to the repository** until GitHub Actions shows exact SHA; PENDING_CI. No extraction precision/recall available. Synthetic model ids in tests are not real inference.

## C2 proof status
Added synthetic tests/test_contract_intelligence_api.py with user permissions, cross tenant, source quarantine, missing model env, OCR uncertainty and medical field access. In test, infer_local is MOCKED and the result must never be claimed as real AI. Python/JS/PG CI of C2 exact SHA PENDING_CI. C1 confirmed Governance run 39058718203 success and MCIAS G1-G7 run 39058718217 success at 453aebde6a8d349207331bbd0bd1b96c5bc34169.

## CI failure and correction C2→C3
At SHA 1d84f576ea75c5632c8d2686c2c8d00021c75212, G1-G7 run https://github.com/overurdream-collab/test2/actions/runs/39059261540 unit job failed test_malformed_model_json_types_are_reviewed_not_executed: TypeError for list-valued provider_code. 389 passed / 20 skipped / 1 failed, postgres-integration and dependency audit successful. Governance and G9 PASS. New code type-checks provider/service and ties numeric value to the candidate quote (not page). Additional negative test for two prices on the same page. New SHA PENDING_CI.

### Source-level tests C4
- Added four synthetic file reader cases in tests/test_contract_documents.py using reportlab/Pillow/openpyxl output read through actual G2 ReaderAgent. Native PDF page and XLSX row mapping, scanned page quarantine, source prompt-as-text. This does not prove Arabic OCR, Qwen3 inference, clause precision/recall or production safety. New SHA PENDING_CI.

### C5 typed compiler tests PENDING_CI
tests/test_contract_rule_compiler.py covers permitted tariff and copay, before/end-exclusive date, provider/tenant mismatch, unsigned draft and missing source, untyped exclusion, forged AST fingerprint, NaN. All new SHA tests pending CI. No financial activation or model inference, no precision/recall.

### C6 Proposal Persistence / PENDING_CI
New synthetic HTTP tests cover server-only candidate creation, duplicate extraction, immutable reviewer decision, missing date refusal, uncertain OCR refusal, cross-tenant denial, and reviewed promotion to inactive ReferencePoint draft. Test file: `tests/test_contract_intelligence_api.py`. PostgreSQL revision `0020_contract_proposals` enforces append-only triggers. **No tests of these changes claimed PASS until new SHA Actions are examined.** No measured clause precision/recall or real Qwen inference.


### C6 exact GitHub evidence and C7 fix (2026-10-17)
- C6 `88ec7edb50a1eb51156fe20470c550518f919d0a`: governance https://github.com/overurdream-collab/test2/actions/runs/39062436942 PASS; G1–G7 https://github.com/overurdream-collab/test2/actions/runs/39062436975 FAIL (5 synthetic API tests HTTP401 from unmocked new router; PostgreSQL assertions expecting old 0019); G9 https://github.com/overurdream-collab/test2/actions/runs/39062436968 FAIL (G9 preflight head and restore); Enterprise https://github.com/overurdream-collab/test2/actions/runs/39062436946 FAIL (same and G8 head). Correctly classified FAIL, no extraction precision.
- C7 repair modifies test-only auth double and target revision constants to existing Alembic head `0020_contract_proposals`. C7 new SHA CI **PENDING_CI**, not assumed passing; model inference remains NOT_RUN.


### C7 actual CI results (verified)
Commit `b161ee75076910f4f535d783d7adccc2c0d0d48e`: Governance https://github.com/overurdream-collab/test2/actions/runs/39062779319 success; G1-G7 https://github.com/overurdream-collab/test2/actions/runs/39062779420 success; G8 https://github.com/overurdream-collab/test2/actions/runs/39062779559 success; G9 https://github.com/overurdream-collab/test2/actions/runs/39062779328 success; Enterprise https://github.com/overurdream-collab/test2/actions/runs/39062779460 success. Previous C6 failures documented; these results cover C7 exact SHA only.

### C8 real-model benchmark — not yet run at author time
`scripts/contract_ai_benchmark.py` pins official Apache-2.0 Qwen3-0.6B model revision `c1899de289a04d12100db370d81485cdf75e47ca` on standard GitHub public CPU runner. Imports actual pretrained weights, runs local loopback inference through `infer_local`, validates exact G2 evidence against synthetic source, records per-case TP/FP/FN, Precision/Recall/FPR and SHA256 of generated responses. Four SYN cases include Arabic, English, mixed, instruction injection. Workflow `.github/workflows/contract-ai-benchmark.yml` automatically starts on PR path change; **PENDING_CI** until actual job/artifact verified. Test cannot measure OCR quality (text-only fixtures). No patient data, private contract or external inference API.


### C8 real pretrained evidence (actual SHA and measurements)
- Commit b20e5c2045d449c17ca3cc930efa0397bcea0ef9; https://github.com/overurdream-collab/test2/actions/runs/39063356685, job qwen-synthetic-cpu completed successfully as *compute*, model official `Qwen/Qwen3-0.6B` revision c1899de289a04d12100db370d81485cdf75e47ca, PyTorch 2.7.1+cpu, Transformers 4.57.1. 4 actual generated outputs (167,157,105,113 tokens); four SYN snippets, 90.7s. Model response hashes available in action logs and artifact 12112685294. Every `infer_local` call rejected response as `ContractExtractionError`; TP=0 FP=0 FN=3, Precision undefined (no predicted positives), Recall 0%, negative-case FPR 0/1, but zero extracted proposals. **Functional extraction FAIL**, regardless of green workflow flag. This is a measured failure, not absence of real inference.
- C9 modifies benchmark to retain safe synthetic completions for diagnosis, and exits FAIL if Recall=0; runs PENDING_CI. Need genuine JSON valid + citation before any model selection. Do not assume 4 corpus cases representative of contracts or Arabic OCR.


### C9 measured failure and C10 format-control experiment
- C9 exact SHA daa4b934f84fd2e7bfefa0ed4de298b8c5178f0a model Action https://github.com/overurdream-collab/test2/actions/runs/39063739175: FAILED as intended with generated response previews. All 4 real outputs were fenced JSON **top-level arrays**, not required `{"clauses":[]}` object; source field name `copy_quote` used instead of `quote`, rule_type invalid (TARIFF, price, contract), cross-context currency AED invented for Arabic copay, malicious document suggested transfer amount but guard did not accept it. Output sizes 167/157/105/113 tokens, TP0 FP0 FN3 Recall0% Precision undefined. This diagnoses format-following weakness, not genuine extraction accuracy.
- C10 reuses existing MIT lm-format-enforcer v0.11.2 Transformers adapter in benchmark local mock server to **honor JSON schema**. It does not constrain to gold answers; eight sections / seven types and null values allowed, data truth still independently validated against quoted source. Added synthetically seeded PostgreSQL test `tests/test_contract_proposal_postgres.py` for raw SQL update/delete of all three new history tables, included in ci.yml. C10 tests PENDING_CI; no new real-accuracy claims.


### C10 failed-source syntax (GitHub CI objective evidence)
Commit `19907cd2d06464769f1816e29aadac374c161e6a` — `mcias/contract_intelligence.py:237` had a double-backslash Python quote-escape issue in the new JSON example. Unit compileall failed https://github.com/overurdream-collab/test2/actions/runs/39064329834, model CPU benchmark failed prior to inference https://github.com/overurdream-collab/test2/actions/runs/39064329875. C10 generated ZERO Qwen tokens and has NO precision/recall measurement, so should not be conflated with C9's true 4 generated outputs / Recall0. C11 fixes literal syntax and awaits exact SHA Actions. Governance C10 passed 39064329849.


### C11 measured schema fix FAIL; C12 stronger pinned CPU model PENDING
- C11 exact SHA bee37b2df08f827c4e9fe53af604c064f8c0c808, model https://github.com/overurdream-collab/test2/actions/runs/39064533187: pretrained Qwen3-0.6B + LM Format Enforcer produced exactly four valid JSON objects {"clauses":[]} for English tariff, Arabic copay, mixed tariff and synthetic prompt injection. Therefore TP0 FP0 FN3, recall0 and undefined precision; no evidence of useful clause extraction.
- C12 compares official Qwen3-1.7B pinned revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e, Apache-2.0, on the **same** 4 gold cases with **unchanged** source validation, constrained decoder and fail-on-zero-recall policy. 1.7B benchmark metrics NOT YET MEASURED; estimated runtime/memory are not measured and may be insufficient on standard CI. Never use SYN 4-case scores as production certification.


### C12 measured 1.7B failure and C13 validator battery
- [C12 actual GitHub CPU run](https://github.com/overurdream-collab/test2/actions/runs/39064879988) on SHA d33c245251d956e98de7c582c75a95fc8a372735: official Apache-2.0 Qwen3-1.7B revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e generated four JSON outputs, all {"clauses":[]}; TP=0 FP=0 FN=3, Recall 0%, Precision undefined. Functional contract extraction FAIL, not a lack of GPU or model weights.
- Standard suites DG, G1–G7, G8, G9 PASS on that SHA; Enterprise suite run 39064879967 had one rate-limiter expectation failure (429 wanted, 200 returned), status FAIL, re-run requested without changing financial behavior.
- C13 `tests/test_contract_gold_battery.py` introduces **20 source-anchored, manually authored SYN cases across all 8 clause sections + 10 adversarial mutations**, each asserts only that deterministic evidence validator distinguishes exact quote from corrupted identity/value. They are *not* real model outputs, and therefore do not count toward AI Precision/Recall. New CI PENDING. Native multipage Arabic/OCR remains incomplete.


### C14 forced-candidate experimental diagnostic (NOT model acceptance)
- Both unconstrained (C9) and LMFE constrained (C11/C12) small pretrained Qwen runs had no validated contract extraction; optional-empty constrained model emitted four empty arrays. C14 **synthetic-only** experiment changes LM Format Enforcer `clauses.minItems` from 0 to 1 for all four examples **including the negative prompt-injection** and records `diagnostic_mode=NONEMPTY_ALL_CASES_INCLUDING_NEGATIVE`. This deliberately probes model *field-population* ability; it is not a safe production decision mechanism and cannot by itself establish real-world precision.
- Validator, source/quote/number/provider checks and human/finance protections are unchanged. The quality job continues to fail on zero recall and now also explicitly fails on any source-verified negative-case false positives; rejected hallucinations remain quarantined and must be reported. Exact C14 pretrained run PENDING_CI.


### C15 stricter date evidence anchor (PENDING_CI)
- New source validator rules require ISO effective dates on PDF/image to appear literally in the **exact clause quote**, not some other paragraph on the same page; structured XLSX dates may come from a separate cell on the **same row**. Three new tests cover two negative date hallucinations and one legitimate same-row tariff. Output with mismatched dates is DRAFT_ONLY/needs_human_review, never an active financial rate.
- Targeted and full CI on C15 SHA PENDING; no clinical/Arabic OCR or LLM precision claim. This is a security fix for reference dates, not proof that model inferred correct dates. If header-only dates are intended, institution must verify explicit reference to the header and structured provenance first.


### C14 measured prompt contamination / C15 regression / C16 correction
- C14 SHA 4a599db8f4b79757b23a1948f4ad042235faa06d real 1.7B + LM Format Enforcer forced-nonempty diagnostic run https://github.com/overurdream-collab/test2/actions/runs/39065549717: all four actual model candidates repeated fixed tutorial provider and service `P7:XRAY`, with false monetary identities in English/Arabic/mixed/injection records. TP0 FP0 FN3, recall0, precision undefined; 4 candidates all quarantined, verified false positives 0. The model did quote each source but failed to derive logical_key/provider/service from it. Independent validator prevented financial activation.
- C15 SHA b677f6ccb4fd4a10554dc261c813cfb89c91a04d G1–G7 https://github.com/overurdream-collab/test2/actions/runs/39065759298 FAIL two synthetic fixtures for legitimate date-source checks: XLSX row expected verified without a date in any cell; reviewer test introduced 2027 end not in contract. Fix fixtures, do not relax source checks. G8/G9/Governance previously passed.
- C16 source prompt no longer includes any fixed sample tariff amount/provider/service/date; describes only JSON fields, allowable sections/types and source-literal identities. Synthetic tests updated to include actual tariff effective dates in same XLSX row and text quote; regression test checks prompt never contains P7:XRAY sample. **C16 CI AND MODEL METRICS PENDING**. No 20+ scanned contract benchmark or production authority.


### C16 syntactic test regression / C17 repair
- C16 commit c1de2fa2e9e26a2a9da695e6397cab8df8c418eb: G1–G7 Actions https://github.com/overurdream-collab/test2/actions/runs/39066030984 unit job FAIL during test collection, SyntaxError in tests/test_contract_intelligence.py at fake response `choices` bracket. C17 adds missing list close; application inference, validators and authorization unchanged. New C17 unit/Postgres/browser/documentation CI PENDING. No evidence yet to classify real Qwen3 extraction as functional PASS.

### C17 actual Qwen benchmark and C18 timing regression correction
- Model run https://github.com/overurdream-collab/test2/actions/runs/39066166029 at C17 SHA 3ee1d648e530086b153354688377b48a37f76055 generated 4 nonempty JSON proposals in test-only forced mode, all quarantined. English H1 source became provider_code 'H1 CONSULT', service_code 'tariff', amount null, logical_key 'provider_code:service_code'; Arabic cost-share 20% returned null amount; mixed H2 likewise null amount and invalid logical_key; injected negative returned incorrect hypothetical provider term. TP=0 FP=0 FN=3, Recall0%, Precision undefined. FINANCIAL ACTIVATION=NONE. This remains failed real-model extraction, even though source guard behaved safely.
- C17 regular DG/G1–G9 PASS; Enterprise https://github.com/overurdream-collab/test2/actions/runs/39066166119 FAIL due one rate-limiter test assuming all 101 requests happen within same real minute. C18 freezes time in synthetic test through wrapping original check_limits with a fixed now; production rate limiter/quotas remain unchanged. New C18 checks PENDING_CI.

### C19 independent cross-clause identity falsification tests (PENDING_CI)
Two new source-specific negative tests verify the AI cannot attach provider H2 to an H1 quote merely because H2 appears elsewhere on the same PDF page, or attach service XRAY and USD to a CONSULT/YER quote when both are present on one page. Same-row XLSX still allowed with independent cells. C19 tests and full PostgreSQL/UI CI have not been observed on exact SHA; report remains PENDING. This is a source-check strengthening, not a successful LLM recall measurement.

### C20 — 20 actual generated synthetic PDF/XLSX/scan source reader cases
- `tests/test_contract_real_files_corpus.py` (new SHA PENDING_CI): 10 different 3-page PDF sources assert page indices, H1/H2 tariff isolation and independent exclusions; 5 real generated XLSX sheets assert per-provider H1/H2/H3 tariff rows, currencies and amount changes; 5 scanned image-only PDFs assert G2 quarantines absent local OCR. No fake reader/model responses. All tests run in memory; no licensed/private source text.
- Important boundary: source parser coverage is **not** real Arabic OCR character accuracy or contract LLM TP/FP/FN/Precision/Recall. These remain NOT_MEASURED. Need actual tested Arabic scanned PDF pack and real Qwen predictions on larger frozen gold. Earlier 20 handcrafted source-anchor texts/10 adversarial tests likewise validate rules but not extraction model quality.
