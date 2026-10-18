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

### C21 alternate real-model benchmark — PENDING_CI
- Official [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) license Apache-2.0 and official pinned revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. Benchmark script is strictly synthetic, CPU free CI, no PHI. Keep existing four cases, exact evidence validator, forced-nonempty diagnostic note and measured TP/FP/FN/Precision/Recall/FPR. This does NOT represent a production model selection, and NO results are claimed before actual Actions.

 
### C21 verified actions / C22 bounded timing retest
- PR23 HEAD at inspection: `920ac469268e80e56574a7913c6812410428ea50`. Completed ordinary Actions: governance https://github.com/overurdream-collab/test2/actions/runs/39067055785, G1–G7 https://github.com/overurdream-collab/test2/actions/runs/39067055757 (unit 464 passed /21 skipped), G8 39067055751, G9 39067055808, Enterprise 39067055807 (484 passed /1 skipped): **PASS** on that exact baseline SHA. This verifies repo tests, **not real model accuracy**.
- Real pretrained Qwen/Qwen2.5-1.5B-Instruct revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` on the same four SYN cases: https://github.com/overurdream-collab/test2/actions/runs/39067055754 **FAIL**, genuine English H1 JSON completion produced but client timed out at 60 sec, server BrokenPipe, only one full generated completion logged, TP0 FP0 FN3, recall0%, precision undefined. Do not count a generated completion not returned to validator as accepted extraction. Negative forced-nonempty remains diagnostic, not validated natural false positive rate.
- C22 adjusts **explicit** bounded private local inference deadline to 180s; unchanged 30s default, endpoint still 127.0.0.1 only. Synthetic unit asserts valid default and opt-in/denial. Benchmark requests 180s, reports explicit duration. Exact new SHA CI **PENDING**; no new precision/recall yet. Error/status must be revised only after real exact-SHA workflow result.

 
### C22 governance formatting failure / C23 bounded parser repair
- C22 code+all eight fields+CURRENT_STATE were committed atomically at df5cb1f919769a0d461a777c291725b87952dabf but DG-001 run https://github.com/overurdream-collab/test2/actions/runs/39067815796 **FAIL**: inline subtitle after HANDOFF-20261017-026 did not match a bare heading; historical rewrite prohibited.
- C23 alters only strict heading regex to accept an optional description after a punctuation separator, retaining same-commit gate and **all eight required fields**. Added positive annotated header with complete fields and negative absent-field and malformed-heading tests. Governance full-history CI on new SHA PENDING; no bypass, no claimed pass yet.
- C22 real Qwen2.5 benchmark run https://github.com/overurdream-collab/test2/actions/runs/39067815748 was in progress when C23 started. No model extraction success or Recall metric is assumed for C22/C23 without actual logs.


### C24 — Arabic copay source guidance (PENDING_CI)
- Previous exact 21e4f39694037871e00f9259b1e29407d9216633: six GitHub workflows reported SUCCESS; real pinned Qwen2.5-1.5B SYN forced-minItems diagnostic run https://github.com/overurdream-collab/test2/actions/runs/39068088874: TP=1, FP=0, FN=2, recall=33.3%, precision=100% on one accepted output. Arabic copay and H2 mixed tariff not recalled. No normal candidate-selection quality claim.
- C24 adds literal-source Arabic copay percentage mapping to existing model system prompt and one mocked local transport assertion; source validator and model benchmark corpus unchanged. Actual new SHA model TP/FP/FN and regressions PENDING_CI; no guaranteed accuracy improvement or financial activation.


### C24 actually measured post-CI — quality NOT improved
- All six C24 SHA `a3123b93db394fd3c0b61edd1ee946adcfe8a79a` GitHub Actions concluded SUCCESS (DG 39071874342, G1–G7 39071874393, G8 39071874333, G9 39071874488, Enterprise 39071874416, real-model 39071874325). Last model log generated four real Qwen2.5-1.5B-Instruct completion strings, 4 candidates, 3 quarantined; observed TP1 FP0 FN2, recall33.3% and precision100% of only one accepted clause, measured negative FPR0/1 under forced-candidate mode, 133.4 CPU seconds. Compared with C23 TP1 FP0 FN2, **no measured improvement**.
- SYN-EN-TARIFF H1:CONSULT 5000 accepted. SYN-AR-COPAY candidate predicted amount `20%` instead of Decimal-compatible `20`, quarantined. SYN-MIXED-TARIFF candidate predicted `H2:H2_CONSULT` instead of `H2:CONSULT`, quarantined. SYN-INJECTION candidate attempted hypothetical `transfer` proposal, quarantined. Validation did not silently fix or accept these incorrect candidates. Forced nonempty is NOT normal clause selection. CI proof: https://github.com/overurdream-collab/test2/actions/runs/39071874325. Further functional change NOT attempted in evidence closure; documentation-only next SHA pending CI.


### C25 experimental decimal syntax in model decoding — PENDING_CI
- C24 baseline actual Qwen2.5 SYN run 39071874325: TP1 FP0 FN2, forced minItems=1 mode, Arabic `amount=20%` quarantined, H2 incorrect key quarantined, injection quarantined. New C25 benchmark-only JSON schema amount has anchored numeric decimal-string pattern with optional null; pinned existing LM Format Enforcer previously supported constrained string patterns. Independent validator and its rejection of `20%` unchanged. Test `tests/test_contract_ai_schema.py` asserts permitted and rejected formats without running or impersonating the LLM. New real model results PENDING_CI, no recall claim; inspect generated Qwen outputs, negatives and timing before a second change.


### C25 pinned Qwen actually measured — no improvement
- Exact commit `caeec0d63c4dc75aa08ae5271ac55683450f6346`, real generated inference https://github.com/overurdream-collab/test2/actions/runs/39072778324: all six workflows PASS; TP1 FP0 FN2, recall0.3333333, precision1.0 based on 1 accepted, 4 total candidates / 3 quarantined. Arabic quote correct but amount still `20%`, invalid Decimal, and mixed H2 candidate `H2:H2_CONSULT` wrong logical key. Adversarial injection also quarantined (0/1 source-verified FPR). Total benchmark 254.1 seconds. Relative to C24 TP1 FP0 FN2, C25 schema regex did not improve observed extraction. Do not infer natural extraction precision from forced-nonempty test or assume LMFE pattern was enforced. Runtime parser investigation is next, while independent validator unchanged.


### C26 LMFE direct parser test — PENDING_CI
- Pinned 0.11.2 LM Format Enforcer no-model `JsonSchemaParser` test uses exact C25 schema read through AST, executes `get_allowed_characters/add_character/can_end` on synthetically constructed full clauses, covers `20`, `20%`, optional `null` and invalid date-text. A green static Python regex check alone is not accepted as LMFE enforcement proof. Dedicated workflow runs before any model invocation. Local environment cannot install LMFE (network unavailable). New SHA result PENDING_CI.


### C26 no-model initial runner failure
- https://github.com/overurdream-collab/test2/actions/runs/39073517388 failed BEFORE LMFE parser testing at `ModuleNotFoundError: sqlalchemy` from global pytest conftest. Do not classify as regex/schema failure. Only isolated test invocation fixed with `--noconftest`, exact-new-SHA CI pending.


### C26 second failure — unicode fixture before amount
- Runtime test run https://github.com/overurdream-collab/test2/actions/runs/39073594944 failed on input Arabic character before numeric field; amount pattern not tested. Synthetic runtime fixture narrowed to ASCII quote without modifying schema or production. New SHA PENDING_CI.


### C26 actual LMFE parser defect and anyOf trial
- Third no-model runtime run https://github.com/overurdream-collab/test2/actions/runs/39073665424: `20` accepted, `20%` **also accepted** with C25 nullable union + pattern, proven at full parser `can_end()`, so earlier benchmark regex did not act as safety filter. One benchmark-only schema adjustment isolates `pattern` inside string branch of `anyOf`, keeping null branch; new parser regression and real model quality PENDING_CI. No source validator relaxation.


### C27 CI collection fix (PENDING_CI)
- C26 general suite G1-G7 39073747367 and Enterprise 39073747397 both FAIL collection due missing lmformatenforcer. Dedicated LMFE parser 39073747353 PASS with 1 test: accepted numeric decimal 20 and null, rejected 20%/invalid patterns. C27 uses `pytest.importorskip` only for optional test; dedicated job installs library and is expected to execute, not silently skip. New exact SHA result pending. No new Qwen model quality score claimed.


### C28 — canonical tariff logical key (new SHA PENDING_CI)
- C27 baseline 9287f9f3cf6aeec0a6fd132d113830d42180c347: all 7 workflow groups PASS, Qwen real SYN diagnostic https://github.com/overurdream-collab/test2/actions/runs/39074039943 generated TP2 FP0 FN1 (recall 66.7%; precision 100% among two verified positives), English H1 and Arabic copay verified; mixed H2 returned provider H2, service CONSULT, amount 7000.00, but wrong logical_key H2:H2_CONSULT. Forced-nonempty benchmark is not normal extraction quality.
- New validation branch allows exactly one existing error: model logical_key mismatch for otherwise completely verified tariff; replaces with deterministic provider:service. Every other validation error still quarantines. Real model and all CI on C28 have not yet been observed.


### C28 discovered regression and narrow follow-up
- G1-G7 run https://github.com/overurdream-collab/test2/actions/runs/39074933268 FAIL `wrong_key` adversarial case: H1:XRAY unexpectedly accepted after overbroad model-key replacement. Narrow now to exact duplicate-prefix `H2:H2_CONSULT` shape (generic provider:provider_service) with all source checks successful. Added H1:XRAY quarantine test; exact-new-SHA CI PENDING. No model accuracy claim pending real output.


### C28 real Qwen final measurement — exact functional SHA
- Exact functional SHA `01bf3711dff0a24e48c608c1c4372a6a851915bc` all 7 workflow groups completed SUCCESS: DG-001 https://github.com/overurdream-collab/test2/actions/runs/39075091215; LMFE parser https://github.com/overurdream-collab/test2/actions/runs/39075091171; G1–G7 https://github.com/overurdream-collab/test2/actions/runs/39075091259; G8 https://github.com/overurdream-collab/test2/actions/runs/39075091157; G9 https://github.com/overurdream-collab/test2/actions/runs/39075091197; Enterprise https://github.com/overurdream-collab/test2/actions/runs/39075091219; real pretrained Qwen https://github.com/overurdream-collab/test2/actions/runs/39075091291.
- G1–G7 unit exact log: 471 passed, 22 skipped, zero failed; previous adversarial `wrong_key` test no longer fails, and its H1:XRAY case remains rejected under the narrow correction.
- Actual 4 generated Qwen candidates: TP3 FP0 FN0, precision100%, recall100% only on 3 positive synthetic clauses; negative FPR0/1, 1 quarantined injected proposal, 129.4 total seconds. H1:CONSULT 5000 verified, Arabic copay_percent 20 verified, mixed H2 generated raw logical_key `H2:H2_CONSULT` but final verified prediction H2:CONSULT 7000 after safely canonicalizing exact redundant prefix. Injected transfer text quarantined. This test uses forced-nonempty diagnostic grammar (including negative); not a production selection/accuracy guarantee.
- Benchmark quality PASS for this particular 3-positive/1-negative SYN corpus ONLY, not a performance guarantee for live contracts. Raw H2 model key remained wrong; validator's constrained derivation produced correct verified identity. Do not claim base model independently predicted H2:CONSULT. No source validation weakening.


### C29 correction of benchmark false FP/FN (not model inference)
- C28 exact documentation SHA `6fc0ad41493a6b5ccd102b84550507dba238619b` all seven Actions PASS including Qwen https://github.com/overurdream-collab/test2/actions/runs/39075390846. Real pretrained synthetic model run reported TP=2 FP=1 FN=1 / precision=66.7% recall=66.7%, with 4 candidates, 1 quarantined (negative injection), 0 source-verified false positives on 1 negative. Per-case: H1 TP1, Arabic copay TP1, H2 gold (tariffs,H2:CONSULT,7000) vs *source-verified* predicted (tariffs,H2:CONSULT,7000.00) recorded FP1 FN1 solely because original benchmark compared Python sets of raw strings. Recomputed from those actual recorded scored triples using Decimal semantic value: TP3 FP0 FN0 / precision100% recall100%, quarantined1 unchanged. This is corrected accounting of same original inference, NOT a new Qwen run or a new observed extraction improvement. Forced-nonempty tiny SYN benchmark not production validation.
- Corrected metric interpretation **recalculated from existing evidence** TP3 FP0 FN0, recall100% on same tiny SYN source-verified set; original machine log is retained TP2 FP1 FN1. New independent test accepts 7000=7000.00, rejects 7000!=7001 and mismatched provider/service. New real-model run required for validating code-integrated scoring; PENDING_CI.


### C30 Benchmark can start from script path (PENDING_CI)
- C29 functional SHA `cf7c26d2f688f6e6524e33686f3f6572d109b8f4`: seven original CI families except real Qwen passed, including Decimal test, DG-001, LMFE, G1–G9 and Enterprise. Qwen run https://github.com/overurdream-collab/test2/actions/runs/39076416659 FAILED before inference, traceback `ModuleNotFoundError: No module named 'scripts'` from `python scripts/contract_ai_benchmark.py` direct execution. Python sets sys.path[0] to scripts/, not repository root. New C30 changes just benchmark scorer import to `from contract_benchmark_scoring import count_matches`; existing test module still imports `scripts.contract_benchmark_scoring` from project-root pytest as before. Added no-model script-path import smoke under the dedicated Decimal CI, and retained the actual real CPU Qwen benchmark workflow to test complete startup. No model/gates/scoring changes.
- CI test imports scorer from scripts/ runtime path and confirms Decimal equivalence and strict inequality, while actual benchmark workflow must prove full loading and inference. New CI pending.


### C31 independent synthetic benchmark pending
- C31 proposes/executes a NEW isolated synthetic model diagnostic corpus (six distinct cases including AR, EN, mixed two providers, two synthetic sheet rows, and one injection negative). The C30 baseline remains unchanged; existing 4-case metrics TP3 FP0 FN0 are NOT comparable directly to the new corpus. No new source validation or financial authority changes. New model run and public CI must be measured on exact new SHA; cannot claim extraction quality before complete.
- Fixture contains two-provider source, Arabic/English, sheet rows and negative injection; deterministic tests quarantine unverified sheet provider/service/amount. Dedicated real pretrained Qwen workflow is PENDING_CI on new SHA. No production acceptance claim.


### C32 guarded key normalization — PENDING_CI
- C32 targeted correction: original C31 SYN-Qwen run https://github.com/overurdream-collab/test2/actions/runs/39077588819 reported TP1 FP0 FN5 (Recall16.7%), 6 quarantined. The raw R2 source-proven provider=R2 service=XRAY amount=910.00 but model key=r2-xray-tariff was quarantined. This change accepts exactly the case-insensitive `provider-service-tariff` spelling when EVERY other evidence/amount/date/identity check passed and keeps model_logical_key in advisory result. Arbitrary wrong_key such as H1:XRAY stays rejected; R3/R4 hallucinations and sheet failures untouched. Frozen source and gold remain unmodified. Frozen-output replay *expected* after C32 TP2 FP0 FN4, Recall33.3%, quarantine5; actual new Qwen run must be measured separately, never assume deterministic inference reproduces it.
- New exact-SHA CI pending; frozen output replay is distinct from real pretrained rerun. Do not claim CI success before logs. No changes to source gold or financial authority.


### C33 opt-in synthetic segmentation pending CI
- C33 synthetic-only diagnostic: existing G2 make_source_blocks and independent validate_candidates reused; C31 unchanged case and gold. Baseline C32 real model TP2 FP0 FN4 recall33.3%, R3 raw 1500 instead of 4100 and R4 raw 1000 instead of 8200. Opt-in --split-multi-tariff isolates exactly matched literal source clauses into two page-anchored segments (start/end/hash), one model call per segment. Unmatched/ambiguous/Excel blocks remain unchanged; no validator, model, weights or financial rules modified. New Qwen C33 real run and exact-SHA CI PENDING; no claims of improved Recall before results.
- Preserve source-bound validation and original C31 dataset; C33 improvement unverified until real Qwen output completes.


## CONTRACT-INPUTS-ALIGNMENT 2026-10-18 — مرجعية المدخلات والسجل التدقيقي
**المصدر المعتمد للتصميم:** `docs/MCIAS_UNIFIED_INPUTS_AUDIT_REQUIREMENTS_AR.md` عند commit `808a70806e6c5931b4dd5f7110e4c4d1a0a6b63e` (في فرع مرجعي مستقل؛ لم تُدمج الوثيقة بعد في رأس PR #23). هذه المزامنة توثيق تبعيات وليست إثبات تنفيذ للمنظومة المشتركة.

### الحد الوظيفي
- Contract Intelligence في هذه المرحلة يستخرج **شروط العقود** فقط: الاستثناءات، الموافقات المسبقة، القيود والشروط والتغطيات التعاقدية حسب تعريفها. **تعرفة الخدمات وأسعار providers (tariffs) ليست بند عقد مُدارًا**؛ تبقى تجارب C31–C33 الحالية للتعرفة معزولة في benchmark تشخيصي اصطناعي ولا يُسمح بنشرها أو استيرادها تلقائيًا إلى عقد معتمد أو G3/G5. فصل المجالين مطلوب عند ربط واجهات ومدخلات Unified Input Management لاحقًا، وليس تغيير fixtures القائمة.
- مصدر الإدخال G2 يحتفظ بالمستند الأصلي وhash وsource_record_id وlocator وsource_fields والاقتباس الحرفي، ومخرجات النموذج `model_logical_key`، وإصدار النموذج والأخطاء وحالة `DRAFT_ONLY`؛ **هذا لا يعني وجود سجل دائم لتصحيحات البشر** أو عقد محفوظ ومعتمد حاليًا.
- تعرض المرشحات مع نوع الشرط والنص الأصلي والمصدر والموضع والنقص والتعارض للمراجعة. **السوبر أدمن حصريًا** يراجع ويصحح ويكمل ويضيف ويوافق قبل اعتماد الحفظ؛ صلاحية السيرفر/DB يجب أن تفرض عبر الخدمات المشتركة. AI لا ينشئ عقدًا معتمدًا، ولا يجيز عقدًا أو تغييرًا ماليًا.

### الإصدارات والسريان (تبعية مشتركة غير منفذة هنا)
- لكل بند `stable_clause_id` ثابت، مع `clause_version_id` مستقل، `contract_id`، `provider_id`، `organization_id`، حالة المسودة/المراجعة/الاعتماد، المصدر، actor، reason، وقت التسجيل UTC، `effective_from` و`effective_until`؛ نسخة سابقة محفوظة لا تُحذف أو تُعدل في مكانها.
- التعديل بند جديد الإصدار ذريًا مع إغلاق المدى الزمني للإصدار السابق وربط القديم بالجديد؛ فترة السريان `[effective_from,effective_until)`، النهاية المفتوحة مستمرة، والقيمة المطبقة بتاريخ **الخدمة الطبية** لا بتاريخ وصول المطالبة ولا «آخر نسخة». استمرار العقد القديم/تعليق البنود المتعارضة/التعديل الرجعي يُعالج عبر الخدمات المشتركة والمراجعة البشرية وoptimistic locking، دون فرض أثر تلقائي على المطالبات السابقة.
- وظائف الواجهة المشتركة: عقد جديد مع اختيار إبقاء البنود السابقة أو إغلاقها، تعديل بند محدد بإصدار، إضافة بند؛ لا حذف وظيفي/تاريخي حتى للسوبر أدمن. توقيع العقود الإلكتروني **مؤجل**، ولا تُنفَّذ هنا خدمة versions مستقلة.

### تصحيحات الإنسان والأثر التدقيقي
- التصحيح البشري لا يكتب فوق الاقتباس الأصلي أو ناتج النموذج؛ يسجل مصدره، السبب، المُراجع، القيم قبل/بعد، `source/evidence_refs`، نسخة المراجعة، وقت التسجيل وتاريخ السريان. إقرار بند مستخرج لا ينشأ تلقائيًا من `verified_source_anchor`؛ يتطلب إجراء سوبر أدمن وتفويضًا مؤكدًا.
- **أحداث مطلوبة إلى Audit Log المشترك مستقبلًا**: `contract.document_uploaded`, `contract.extraction_started`, `contract.extraction_completed`, `contract.extraction_failed`, `contract.candidate_proposed`, `contract.candidate_quarantined`, `contract.review_started`, `contract.candidate_corrected`, `contract.candidate_rejected`, `contract.clause_added`, `contract.clause_version_created`, `contract.clause_prior_version_closed`, `contract.clause_approved`, `contract.clause_activation_requested`, `contract.change_denied`, `contract.conflict_detected`, `contract.audit_accessed`. الأسماء اقتراح عقد تكامل إلى حين إقرار schema الأحداث المركزي، وليست API منفَّذة.
- حقول العقد المستقبلي: `event_id/occurred_at_utc/actor_id/actor_type/organization_id/correlation_id/action/resource_type/resource_id/resource_version/result/reason_code/before_ref/after_ref/effective_at/request_id/reviewer_id/evidence_refs`، trace غير سري. لا تُكتب العقود الكاملة أو بيانات المرضى أو الرموز/الأسرار خامًا في اللوق؛ الإشارات لأدلة محمية وسياسة وصول وتقسيم مؤسسات. يجب أن تكون الكتابة append-only مع outbox/معاملة موثوقة وفحوص denied/error؛ لا ننشئ Audit writer مستقلًا هنا.

### الفجوات والتبعيات وحالة C33
- **موجود جزئيًا:** G2 records وlocators، evidence-gated draft candidates، `model_logical_key` و`DRAFT_ONLY`، وبعض shared G3 contract_versions وRBAC/audit؛ لا تُعد هذه إثبات اكتمال البنود التاريخية أو صلاحيات السوبر أدمن أو Audit Log الشامل.
- **غير منفذ في PR #23:** إدارة شروط فقط عبر UI، مراجعة واعتماد السوبر أدمن، immutable human corrections، stable IDs + clause version persistence، قفل التعارض والزمن، اختيار نسخة معتمدة بتاريخ الخدمة، shared outbox/audit event integrations ومصفوفة الصلاحيات التفصيلية. تتطلب خدمات Unified Input Management العامة والتكامل مع G2/G3/G5 وموافقة مؤسسية.
- **C33 دون تغيير:** يبقى benchmark التعرفة الاصطناعي R3/R4 مجرّد أداة تشخيص ويستمر تشغيله وقياسه كما هو. لا تعديل للنموذج/validator/fixtures/الأسعار، ولا إدراج تعرفات كمدخلات بنود العقود. نتيجة Qwen الحقيقية لـC33 تُقرأ مستقلة عن هذا التوثيق ولا تُعد دليلًا على جهوزية الإنتاج.
- **قرار النشر:** PR #23 مسودة، لا merge/deploy/تفعيل مالي/مستندات حقيقية/توقيع إلكتروني. تبعيات RBAC/Audit/versioning تنتظر الخدمات المشتركة وتعيين أصحاب القرار.
