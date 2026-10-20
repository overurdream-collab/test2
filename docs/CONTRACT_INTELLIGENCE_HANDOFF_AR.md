# Contract Intelligence — استلام فوري للمبرمج وCodex

**مشروع:** overurdream-collab/test2 / branch feat/mcias-contract-intelligence / base PR #22 (unmerged). **R0 status:** research and architectural specification documented; no model inference demonstrated. Read CURRENT_STATE and EXECUTION_JOURNAL first; never interpret docs as deployed behavior.
## Do first
1. Fetch latest branch HEAD from GitHub, compare with parent feat/temporal-reference-inputs-and-four-outcomes and review linked Draft PR.
2. Read docs/CONTRACT_INTELLIGENCE_OPEN_SOURCE_RESEARCH_AR.md, ARCHITECTURE, TEST_REPORT, DECISION_REGISTER; code: ingestion/reader_agent.py, orchestrator.py, reference_points.py, reference_rule_bridge.py, app.py, models_ingestion.py and 0019.
3. Run python -m pip install -e '.[test]' then python -m pytest -q tests/test_g2_ingestion.py tests/test_reference_rule_bridge.py tests/test_reference_points_and_outcomes.py tests/test_reference_points_http_security.py; use isolated MCIAS_TEST_DATABASE_URL for PG and Actions for comprehensive checks.
4. **Next task:** add synthetic generation and JSON schema evidence validator in a small commit with HANDOFF and CURRENT_STATE; then model inference adapter behind disabled-by-default flag; do not persist AI output as ReferencePoint automatically.
5. Real model is NOT_RUN. No model version/weights/hash, benchmark, accuracy metric or GPU availability has been established. Have on-prem isolated runtime approved before using any live institution input.
## Invariants
Never merge or deploy, pay for models, expose PHI, change main, update approved financial history, call G5 directly from LLM, create A1, approve points without institutional bound signature. Each commit must contain 8 HANDOFF fields + CURRENT_STATE and developer/acceptance updates if applicable; CI on exact SHA, PENDING_CI otherwise. Handoff must state precise remaining work.

## C1 first code commit
Review mcias/contract_intelligence.py and tests/test_contract_intelligence.py; check actual GitHub Actions. The model endpoint is deliberately only 127.0.0.1/localhost with /v1/chat/completions; no runtime configured so real Qwen inference is NOT_RUN. Next must connect G2 record/job tenant-scoped API and preserve field-level permissions, then begin true model benchmarking. No ReferencePoint inserted automatically.

## C2 next steps
Preview API lives in mcias/contract_intelligence_api.py, route app.py, browser reference_points_view.js. Requires G2 document status extracted, trusted locator fields, existing RBAC and explicit local model vars. No persistence or automatic approval; C2 tests mock model. Check exact SHA CI, fix failures, run isolated on-prem model with SHA/weights revision then build persisted candidate review workflow as new additive migration, updating expected G9 migration head as appropriate.

### C3 targeted regression
Fixes failing G1-G7 unit on 1d84f576: provider_code list caused TypeError. Newly added two-prices-same-page test. Look up CI for C3 exact SHA and record evidence before any further work. C1 local-only LLM runtime still NOT RUN.

### Resume C4
- Run python -m pytest -q tests/test_contract_documents.py alongside tests/test_contract_intelligence.py and tests/test_contract_intelligence_api.py. Exact CI required; if PDF parser test fails inspect source MIME/file_scanner limits before altering G2. No institutional data, no new parser. Next typed rules and real local model inference.

### C5 resume
Read mcias/contract_rule_compiler.py + tests/test_contract_rule_compiler.py and check HEAD CI. Diagnostic compiler never executes financial policy. Next a local model real inference with weight/model revision and replayable samples, then persistent proposals and independent human review; no activation.

### C6 resume: source-anchored persisted proposals
- New models_contract_proposals.py and migration 0020 implement tenant-bound immutable proposal/review/promotion history. contract_proposals_api.py defines /extract, /documents/{id}/proposals, /proposals/{id}/review and /promote. No raw AI result supplied by client is accepted. Source G2 fields are checked for permissions again on review. Only independently reviewed complete candidates promote to an INACTIVE ReferencePoint draft, not to finance execution.
- Tests: tests/test_contract_intelligence_api.py; PostgreSQL and full CI on new SHA PENDING. Real Qwen inference, Arabic OCR benchmark, UI reviewer journey, institutional signatures all NOT_DONE. Never merge or deploy.


### C7 CI fix resume
C6 SHA 88ec7edb had FAIL on tests due mock-auth fixture and migration head; see Test Report. C7 supplies fixture and 0020 head updates (test-only and G9 preflight). Run exact-head G1–G7, G9, Enterprise and DG Actions. Real local Qwen, UI review and signed approval are still open and must not be represented as complete. Never merge or enable financial authority.


### C8 handoff — real pretrained proof and human UI
The `reference_points_view.js` drawer now supports persisted /extract and a separate review/propose UI for users having `reference.read` + `ingestion.read`, and `reference.approve` for human review. Branch C8 adds `scripts/contract_ai_benchmark.py` and `.github/workflows/contract-ai-benchmark.yml` for local loopback Qwen3-0.6B model, pinned SHA, 4 synthetic cases and measured evidence. Inspect exact Actions before saying any model run passed. Hosted public standard GitHub runners are free; no external sensitive records or financial activation. If the synthetic benchmark fails, record model loading or malformed-JSON error and continue only with evidence. Expand Arabic/scanned/Excel gold corpus before complete acceptance. Do not merge or start A1.


### C9 actual pretrained model blocker
C8 real Qwen3-0.6B generated 4 outputs but zero source-verified clauses: TP0 FP0 FN3, Recall0, Precision undefined (Action run 39063356685). Diagnose as model JSON schema mismatch, not a working functional agent. C9 script adds safe previews of *synthetic-only* outputs and fails the quality job when zero useful clauses. Fetch new benchmark logs/artifact; update reporting with raw evidence. Never send real insurance files to a public runner. Remaining: prompt/schema correction, repeatable real inference, larger 20+ contracts, Arabic OCR, review UAT, signatures, no main merge or A1.


### C10 — JSON-constrained pretrained experiment + raw SQL guard
C9 SHA daa4b934f84fd2e7bfefa0ed4de298b8c5178f0a: all ordinary governance/G1–G9/Enterprise workflows success, but real Qwen3-0.6B benchmark FAILED https://github.com/overurdream-collab/test2/actions/runs/39063739175 (TP0 FP0 FN3, malformed fenced arrays and wrong schema). No acceptance. C10 adds lm-format-enforcer v0.11.2 **benchmark-only** constrained JSON output, generic few-shot prompt, and tests/test_contract_proposal_postgres.py to prove proposed/review/promoted immutable tables resist direct SQL changes. Test on exact C10 SHA pending; review CI, see model generated hashes/source anchors, fix only without bypassing validator. Real patient/private files forbidden, no production approvals, deployment, PR merge or A1.


### C11 resume — corrected prompt quotes
C10 new real-model harness could not import `mcias.contract_intelligence` due accidental doubled escapes before embedded JSON quote characters at line 237. CI https://github.com/overurdream-collab/test2/actions/runs/39064329834 and model run 39064329875 FAIL. C11 repairs Python syntax in prompt only, not validator/financial guard. Verify compileall, all CI, constrained pretrained model JSON accuracy and PostgreSQL immutable test after commit; until observed all PENDING. No merge, production, real files or A1.


### C12 next action
- C11 real-model evidence at SHA bee37b2d: JSON correct but every valid synthetic source returned zero clauses; Actions 39064533187 functional FAIL (TP=0, FP=0, FN=3). The new C12 source-only benchmark compares Qwen3-1.7B official revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e without modifying application runtime/finance.
- Inspect Contract AI real-model synthetic benchmark Actions on new SHA, capture actual model load/memory errors if any and full TP/FP/FN/response SHA. All work on Draft PR23 child of unmerged PR22; no PHI/public uploads, paid servers, merge, production, A1 or automatic finance.


### C13 resumption
- Exact C12 1.7B benchmark run 39064879988 was an evidence-backed **FAIL**: 4 empty structured outputs, TP0 FP0 FN3. Avoid classifying 0 FP with no model positives as success.
- New `tests/test_contract_gold_battery.py`: 20 positive synthetic source snippets spanning eight categories and 10 intentionally invalid updates; run `pytest -q tests/test_contract_gold_battery.py` as unit tests. This verifies only quote/type/dates/provider checks, not actual AI extraction or OCR.
- Enterprise run 39064879967 failed a rate-limit check; rerun requested and investigation open. Fetch fresh branch head and checks before proceeding. Remaining: actual validated clauses from pretrained model, large document gold, Arabic OCR and signature-bound institutional UAT. No merge/main/production/A1.


### C14 — diagnostic differentiation
- C13 deterministic 30-case gold-anchoring suite passed as part of G1–G7 (run 39065318369), not AI benchmark. C14 test-only script forces at least one structured proposal in ALL four SYN model prompts (including adversarial negative), while source validator stays strict and false-positive gate is explicit. No production runtime or signed finance changes.
- Retrieve C14 exact GitHub Actions output: how many candidates generated, how many quarantined, TP/FP/FN on verified source anchors, any model/timeouts and artifact hashes. Do NOT use forced-nonempty metrics as normal model-selection accuracy. Next: assess more capable model or two-stage classifier+extractor; expand 20+ real-structure SYN documents and local Arabic OCR.


### C15 date lineage
- Open mcias/contract_intelligence.py `validate_candidates` and tests/test_contract_intelligence.py: for PDF/image, verify date inside quote; for sheet/row, permit date in same persisted G2 record fields. Unknown or inferred effective date must not silently authorize tariff version.
- Run targeted pytest + full CI and inspect C14 forced model experiment before applying any other changes. No actual contract data/public runner use, no main merge, production, signatures, A1 or financial rule activation.


### C16 resumption — example contamination and grounded dates
- C14 real Qwen diagnostic all 4 generated candidates copied P7:XRAY from system-prompt sample and got quarantined (run 39065549717). C15 stricter date proof rightly exposed two bad synthetic fixtures, causing G1–G7/Enterprise failures (run 39065759298). C16 removes prompt sample constants and corrects test *source quote and row* (not validator). Check new full CI and real model errors/TP/FP/FN.
- Review mcias/contract_intelligence.py, tests/test_contract_intelligence.py, tests/test_contract_intelligence_api.py. Do not re-introduce numeric/provider examples into system instruction; do not drop source date validation. No production, main/merge, A1 or model-specific financial authority.


### C17 resume
- Latest C16 unittest regression was SyntaxError at fake local model JSON `choices` list (Actions run 39066030984), not a production code import issue. New C17 fix is test-only. Review exact C17 G1–G7, G8, G9, Enterprise and model bench results after commit; preserve strict source date evidence and no hardcoded system-prompt tariff identities. Continue only Draft PR23, no main merge, deployment or A1.

### C18 next resume — timing test and actual model blocker
C17 real-model run 39066166029 FAIL: four source-unverified proposals, wrong IDs and missing numeric values, Recall0/3; example contamination fixed but pretrained extraction still unusable. All G1–G9 regular tests and governance PASS, Enterprise 39066166119 FAIL one intermittent wall-minute-rollover limit test. C18 test-only fix pins rate-limit now while still executing actual middleware; CI on new SHA PENDING. Inspect current PR23 head, all C18 Actions, then resume rigorous real-model/source tests. Never use private data or bypass signed G3/G5 controls, no merge or A1.

### C19 — PDF tariff identity independence
Read mcias/contract_intelligence.py validation of provider/service/currency: PDF/image uses one exact quote, structured sheet only same G2 source row, besides numeric/date checks. Two adversarial tests added to tests/test_contract_intelligence.py; examine GitHub Actions on latest C19 SHA and fix regressions with new DG-001 event. No model finance activation, no main merge, no A1. Real model still under independent review and broader gold benchmark missing.

### C20 reproducible binary document corpus
- Open `tests/test_contract_real_files_corpus.py`; in-memory generated files only, 10 3-page PDF, 5 XLSX tariff sheets with 3 providers, 5 scanned image-only PDFs without enabled OCR. Run `python -m pytest -q tests/test_contract_real_files_corpus.py tests/test_contract_documents.py`. Expect strict page/row locators and quarantine; no sample data uploaded.
- This is NOT pretrained LLM extraction or Arabic OCR validation. Review exact C20 SHA CI, pending current pretrained benchmark, and subsequent Arabic OCR/model corpus. Do not merge or use production data; G3/G5 unaffected.

### C21 model comparison experiment
- Inspect pinned Qwen2.5-1.5B-Instruct (Apache-2.0) test-only benchmark in scripts/contract_ai_benchmark.py. Run Actions on exact new SHA, collect model revision, actual generated response hashes, candidates, quarantined, TP/FP/FN and errors. Compare to Qwen3 0.6B/1.7B previously measured Recall0. Production model stays unconfigured; forced-nonempty diagnostic is explicitly not acceptable for autonomous contract decisions. No main merge, A1, deployment, real PHI or financial activation.

 
### C22 next operator — no duplicate commits
- Fetch **latest** `feat/mcias-contract-intelligence` HEAD and PR23; user has forbidden conflicting edits. C21 SHA `920ac469268e80e56574a7913c6812410428ea50` all five regular GitHub suites PASS, but Qwen2.5-1.5B-Instruct SYN benchmark run 39067055754 FAIL (60s loopback timeout, BrokenPipe, TP0 FN3). It emitted a plausible sourced English tariff but client could not verify it before timeout.
- C22 is narrowly scoped: `mcias/contract_intelligence.py` explicit timeout maximum 180s instead of 60, **default production 30 remains**; `scripts/contract_ai_benchmark.py` explicitly passes 180 and labels metric; unit test proves default30/opt-in180/reject181 or 0. It does not change finance/G3/G5/tenant/quoted-source validation. Inspect exact new CI and test artifact before calling C22 a pass.
- Unfinished AI quality on frozen gold (20+ files), Arabic scanned OCR, signed financial authority and independent reviewer/browser end-to-end. No merger of PR23 or PR22, production deployment, institutional datasets in free cloud or A1 work.

 
### C23 governance repair and current blockers
- C22 SHA df5cb1f919769a0d461a777c291725b87952dabf has DG FAIL at 39067815796 solely due strict heading grammar despite eight required fields. C23 updates parser and tests to support `### HANDOFF-ID — description` but no exemption: 8 fields, original commit trace and CURRENT_STATE required. Inspect exact C23 DG-001 run before proceeding; do not rewrite C22 SHA or force push.
- C22 opt-in model benchmark local CPU 180s versus production default 30s, real model quality still unproven pending full Actions. Read model-run logs, preserve false-positive guards; no PHI, merge, G3/G5 signed activation, production model or A1.


### C24 precise handoff — 2026-10-18
- PR23 child of unmerged PR22; C23 head 21e4f39694037871e00f9259b1e29407d9216633 all six workflows success, yet real Qwen2.5 forced SYN extraction TP1 FP0 FN2. C24 prompt-only Arabic patient copay percentage-from-source cue plus mock test in one DG-001 atomic commit. Source gate untouched. Check latest head + CI and actual model case metrics before second code change; not approved for production/main/G3/G5/A1.


### C24 completed measurement / next narrow iteration
- Actual C24 `a3123b93db394fd3c0b61edd1ee946adcfe8a79a` all 6 GitHub workflows PASS. Real Qwen2.5 generated 4 SYN proposals: TP1 FP0 FN2, unchanged recall33.3%, 3 quarantined; Arabic candidate amount `20%` invalid, mixed H2 logical_key `H2:H2_CONSULT` wrong, injection quarantined. Log https://github.com/overurdream-collab/test2/actions/runs/39071874325. Keep old failed historical results; do not mark model accepted. Next developer examines existing LM Format Enforcer schema's amount:string and possible typed decimal constraint, while preserving strict `_numeric`/source and only one further change after research/tests. PR22/23 Draft, no patient data or G3/G5 finance, production or A1.


### C25 resume — format constraint trial
- At baseline documentation SHA d81a78790b11e23e7b866973d1b80b4347461d83, C24 real model recalled 1/3 (TP1 FP0 FN2). C25 experiment constrains `amount` to numeric string or null **only within SYN Qwen benchmark**; standalone syntax test covers percent suffix and date-like strings. All new-SHA CI and real pretrained model quality PENDING_CI. If pinned LMFE pattern handling errors or negative cases worsen, record failure without weakening source validation. Do not touch application model gateway, human review, G3/G5 or A1. Continue at latest PR23 SHA.


### C25 evidence closure / next investigation
- Baseline C25 `caeec0d63c4dc75aa08ae5271ac55683450f6346` Actions DG/G1-G9/Enterprise and real CPU Qwen benchmark all PASS. **Actual extraction remains TP1 FP0 FN2**; the amount syntax regex in benchmark did not prevent model `20%`; H2 logical key still wrong. Details and logs https://github.com/overurdream-collab/test2/actions/runs/39072778324. No second functional adjustment made in this closure. Before touching schema again, confirm pinned LM Format Enforcer nullable-string regex token enforcement with a runtime test. Never weaken independent source gate, user approval, finance or privacy. PR22/PR23 remain DRAFT.


### C26 next operator
- Review standalone `Contract LMFE schema runtime probe` CI on latest PR23 commit: exact C25 schema nullable decimal string, `20` expected accepted, `20%` rejected with pinned LMFE 0.11.2, no pretrained generation. No code change to benchmark until result examined; obey DG-001 and do not change source validation, G3/G5 or deploy.


### C26 test runner repair
- Existing minimal no-model LMFE test was blocked before collection by unrelated global pytest conftest SQLAlchemy dependency (run 39073517388). New workflow invocation explicitly omits unrelated conftest; no LMFE schema or evidence validator changed. Inspect next run before concluding pattern behavior.


### C26 exact parser isolation
- Previous run 39073594944 showed non-ASCII quote rejection at offset 49 before `amount`; use new ASCII-only synthetic quote in dedicated parser test to isolate pattern behavior. Do not draw conclusion on nullable pattern until fresh CI result.


### C26 single schema remediation checkpoint
- Isolated no-model run 39073665424 proved C25 LMFE nullable-union amount `pattern` accepts `20%`, contrary to intent. SYN-only schema changed to `anyOf` explicit patterned string and null; two regression tests updated. Inspect next exact SHA parser CI BEFORE calling fix successful. All core source provenance/financial/reviewer guards unchanged; no extra feature allowed.


### C27 handoff
- On C26 SHA c9ea45e950bf480b75b929694f9621e807037e7a, independent LMFE 1 passed; general suites failed optional import. One test-only `pytest.importorskip` fix committed with DG-001 docs, no runtime or benchmark change. Verify new SHA general suites plus dedicated test executed, inspect actual Qwen results. No production/main/finance/A1.


### C28 next operator
- C27 baseline 9287f9f3cf6aeec0a6fd132d113830d42180c347: all 7 workflow groups PASS, Qwen real SYN diagnostic https://github.com/overurdream-collab/test2/actions/runs/39074039943 generated TP2 FP0 FN1 (recall 66.7%; precision 100% among two verified positives), English H1 and Arabic copay verified; mixed H2 returned provider H2, service CONSULT, amount 7000.00, but wrong logical_key H2:H2_CONSULT. Forced-nonempty benchmark is not normal extraction quality.
- One key derivation on fully verified tariff candidate, with cross-provider and cross-service adversarial tests; C28 exact-SHA CI and model quality PENDING. Inspect actual generated outputs and source-error quarantine, don't tune another model field before CI. No merge, production or G3/G5.


### C28 narrow repair follow-up
- C28 first implementation failed security gold battery wrong_key (39074933268). New SHA limits redundant-key canonicalization to `provider:provider_service`, leaves arbitrary `H1:XRAY` rejected. Need exact CI and actual Qwen results before success claim. No other agent/finance or release.


### C28 closed functional SHA and handoff
- Exact functional SHA `01bf3711dff0a24e48c608c1c4372a6a851915bc` all 7 workflow groups completed SUCCESS: DG-001 https://github.com/overurdream-collab/test2/actions/runs/39075091215; LMFE parser https://github.com/overurdream-collab/test2/actions/runs/39075091171; G1–G7 https://github.com/overurdream-collab/test2/actions/runs/39075091259; G8 https://github.com/overurdream-collab/test2/actions/runs/39075091157; G9 https://github.com/overurdream-collab/test2/actions/runs/39075091197; Enterprise https://github.com/overurdream-collab/test2/actions/runs/39075091219; real pretrained Qwen https://github.com/overurdream-collab/test2/actions/runs/39075091291.
- G1–G7 unit exact log: 471 passed, 22 skipped, zero failed; previous adversarial `wrong_key` test no longer fails, and its H1:XRAY case remains rejected under the narrow correction.
- Actual 4 generated Qwen candidates: TP3 FP0 FN0, precision100%, recall100% only on 3 positive synthetic clauses; negative FPR0/1, 1 quarantined injected proposal, 129.4 total seconds. H1:CONSULT 5000 verified, Arabic copay_percent 20 verified, mixed H2 generated raw logical_key `H2:H2_CONSULT` but final verified prediction H2:CONSULT 7000 after safely canonicalizing exact redundant prefix. Injected transfer text quarantined. This test uses forced-nonempty diagnostic grammar (including negative); not a production selection/accuracy guarantee.
- No further code changes requested or applied. Closure commit docs-only DG-001, own CI PENDING_CI. PR22/23 remain Draft; no publication/merge or finance. Future operator must verify current PR HEAD and preserve negative provider/service/key regression coverage.


### C29 handoff
- C28 exact documentation SHA `6fc0ad41493a6b5ccd102b84550507dba238619b` all seven Actions PASS including Qwen https://github.com/overurdream-collab/test2/actions/runs/39075390846. Real pretrained synthetic model run reported TP=2 FP=1 FN=1 / precision=66.7% recall=66.7%, with 4 candidates, 1 quarantined (negative injection), 0 source-verified false positives on 1 negative. Per-case: H1 TP1, Arabic copay TP1, H2 gold (tariffs,H2:CONSULT,7000) vs *source-verified* predicted (tariffs,H2:CONSULT,7000.00) recorded FP1 FN1 solely because original benchmark compared Python sets of raw strings. Recomputed from those actual recorded scored triples using Decimal semantic value: TP3 FP0 FN0 / precision100% recall100%, quarantined1 unchanged. This is corrected accounting of same original inference, NOT a new Qwen run or a new observed extraction improvement. Forced-nonempty tiny SYN benchmark not production validation.
- New score helper pure Decimal, no modification to independent contract source validation; added separate no-model CI plus original real model workflow triggers because benchmark script changed. Latest SHA checks pending. Do not confuse corrected old score with a new model inference result.


### C30 operator resume
- C29 functional SHA `cf7c26d2f688f6e6524e33686f3f6572d109b8f4`: seven original CI families except real Qwen passed, including Decimal test, DG-001, LMFE, G1–G9 and Enterprise. Qwen run https://github.com/overurdream-collab/test2/actions/runs/39076416659 FAILED before inference, traceback `ModuleNotFoundError: No module named 'scripts'` from `python scripts/contract_ai_benchmark.py` direct execution. Python sets sys.path[0] to scripts/, not repository root. New C30 changes just benchmark scorer import to `from contract_benchmark_scoring import count_matches`; existing test module still imports `scripts.contract_benchmark_scoring` from project-root pytest as before. Added no-model script-path import smoke under the dedicated Decimal CI, and retained the actual real CPU Qwen benchmark workflow to test complete startup. No model/gates/scoring changes.
- Check exact latest SHA run for model-generated synthetic TP/FP/FN and all guards, particularly synthetic H2 monetary precision and negative injection. Never infer full inference from smoke alone.


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


## DG-001 — 2026-10-20 exact-SHA documentation reconciliation
**Baseline inspected:** PR #23 Draft `39a4a9b93e9eb04ea7c09c8c155c3e08f38c6ec0`. This section records newly inspected *completed CI* on that exact source SHA; earlier C31/C32/C33 model failures/successes and their dates remain historical, not overwritten.
**Ten completed successful workflows on inspected source SHA:**
- G1-G7 [39142051829](https://github.com/overurdream-collab/test2/actions/runs/39142051829) PASS (unit, dependency audit, PostgreSQL).
- G8 [39142051813](https://github.com/overurdream-collab/test2/actions/runs/39142051813) PASS.
- G9 [39142051863](https://github.com/overurdream-collab/test2/actions/runs/39142051863) PASS.
- Enterprise [39142051799](https://github.com/overurdream-collab/test2/actions/runs/39142051799) PASS.
- Documentation governance [39142051833](https://github.com/overurdream-collab/test2/actions/runs/39142051833) PASS.
- Contract LMFE schema no-model [39142051800](https://github.com/overurdream-collab/test2/actions/runs/39142051800) PASS.
- Contract Decimal benchmark no-model [39142051864](https://github.com/overurdream-collab/test2/actions/runs/39142051864) PASS.
- Real pretrained Qwen synthetic baseline [39142051770](https://github.com/overurdream-collab/test2/actions/runs/39142051770) PASS job: **TP3 FP0 FN0** in its small diagnostic source-specific set; does not establish general extraction.
- Independent synthetic model benchmark [39142051801](https://github.com/overurdream-collab/test2/actions/runs/39142051801) PASS *execution*, **TP2 FP0 FN4, Recall 33.33%** on 6 ground-truth positives; substantial extraction quality blocker.
- C33 isolated tariff segmentation [39142051824](https://github.com/overurdream-collab/test2/actions/runs/39142051824) PASS *execution*, **TP2 FP0 FN4, Recall 33.33%** on same limited independent synthetic cases; segmentation not proven to improve recall on that SHA.

**Crucial distinction:** CI SUCCESS means the model ran, validator and quality-reporting workflow completed as designed. It does **NOT** mean its model recall/coverage passed a production quality threshold. Preserve model negatives and falsifiable benchmarks. Metrics reflect synthetic tariffs and remain separate from governed Contract Intelligence clause activation. Tariffs are not to be promoted from C33 into approved G3/G5 units or A1 fee authority.
**Missing functional approvals:** real independently expert-labelled multi-layout Arabic/English PDF clause benchmark, contract clause management and service-date legal versioning, super_admin-only server-side governance, original encrypted G2 evidence and source-level Palermo reattestation, Shared Audit integrated correction history, G6/G7 operational human signoff. No activation, autonomous financial decision, merge or deploy.
**Migration compatibility READ-ONLY:** PR23 `alembic/versions/0019_reference_points.py` (parent 0018) → `0020_contract_proposals.py` vs PR25's `0019_input_clauses.py` (parent 0018) → `0020_manual_contract_metadata.py`. These are divergent chains, not a duplicate literal revision ID. Standalone green CI is not a proof that a combined Alembic head is valid. Independent cross-branch report is recorded on PR25 as `docs/DG-001_ALEMBIC_BRANCH_COMPATIBILITY_READ_ONLY_20261020_AR.md` at https://github.com/overurdream-collab/test2/blob/feat/mcias-input-triactions-e2e/docs/DG-001_ALEMBIC_BRANCH_COMPATIBILITY_READ_ONLY_20261020_AR.md . No Alembic command, migration, merger or DB write was executed.
**SHA freshness:** this documentation correction itself creates a new PR23 commit. The ten listed green runs are for `39a4a9b...` only; check the new head and its own CI, and never copy earlier green to a new SHA without matching evidence. **NO MERGE / NO DEPLOY / NO PRODUCTION CONTRACT AUTHORITY.**
