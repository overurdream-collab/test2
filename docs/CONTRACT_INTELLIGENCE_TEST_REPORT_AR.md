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
