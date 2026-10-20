# MCIAS v2.0 — نقطة الاستئناف الحالية (CURRENT STATE)

**آخر تحديث موثق:** 2026-10-17.  
**فرع التطوير:** `feat/temporal-reference-inputs-and-four-outcomes` — [PR #22 مسودة](https://github.com/overurdream-collab/test2/pull/22).  
**خط أساس التوثيق الجديد:** `8bdb43fd467f5766ecaa8cbc48f379dea99e17cb`؛ يخضع كل Commit تالٍ لسياسة [DG-001](DOCUMENTATION_GOVERNANCE_AR.md).  
**فرع `main`:** النسخة الهندسية السابقة المستقرة بالنسبة لـPR #22؛ لم يُدمج عمل PR #22 فيه.  
**المخطط الأعلى للوكلاء:** [PR #19 مسودة](https://github.com/overurdream-collab/test2/pull/19) ولم يُدمج بعد.

## الحالة الآن
- موجود قبل هذه السياسة: إدخالات G3 وعقود وتعرفة مقدمي خدمة، G5 فاحصون ثمانية/Decimal، Palermo-2، G6/G7/G8، وحماية مؤسسية؛ اقرأ الدليل الرئيسي.
- ضمن PR #22: إدارة بنود مستقلة وإصدارات زمنية مغلقة دون حذف؛ توفيق قراءة فقط مع تعرفة G3 وسياسة G5 الموقعة؛ شاشة بنود بثمانية أقسام؛ أربع نتائج تدقيق CSV أولية.
- **أُضيف الآن:** سياسة توثيق إلزامية DG-001، سجل حالة واحد، قالب Pull Request وفحص CI للـCommits الجديدة. هذا التنظيم **لا ينشر** التطبيق ولا يغير مبالغ المطالبات.
- **غير منفذ:** استخراج بنود العقود بـAI، مترجم شامل لجميع الشروط، تفعيل مؤسسي بتوقيع خاص ببصمة البند، إثبات اكتمال سجل المستفيدين، حسم الرفض القطعي، SavingsLedger الحقيقي، تشغيل A1–A5.
- **الاعتماد المؤسسي:** G0–G9 ما زالت OPEN. لا بيانات مرضى حقيقية أو خدمات مدفوعة أو تفعيل رفض/دفع آلي.

## الحالة المثبتة وآخر أدلة اختبار
- آخر إثبات كامل قبل هذه السياسة: Commit `8bdb43fd467f5766ecaa8cbc48f379dea99e17cb`. نجاح مجموعات G1–G7 وG8 وG9 والمتصفح:
  - https://github.com/overurdream-collab/test2/actions/runs/39055254296
  - https://github.com/overurdream-collab/test2/actions/runs/39055254333
  - https://github.com/overurdream-collab/test2/actions/runs/39055254261
  - https://github.com/overurdream-collab/test2/actions/runs/39055254364
- **اختبارات Commit DG-001 الأول** `d7009e6c37f86e51182a7825d39c58ba8ad7dd31`: فحص [Documentation governance](https://github.com/overurdream-collab/test2/actions/runs/39055995211) **PASS**؛ [G1–G7](https://github.com/overurdream-collab/test2/actions/runs/39055995228) **PASS**؛ [G8](https://github.com/overurdream-collab/test2/actions/runs/39055995152) **لم تُراجع نتيجته ضمن أول شهادة**؛ [G9](https://github.com/overurdream-collab/test2/actions/runs/39055995077) **PASS**؛ [المتصفح](https://github.com/overurdream-collab/test2/actions/runs/39055995255) **لم تُراجع نتيجته ضمن أول شهادة**. راجع حالة CI مباشرة.
- **آخر SHA تحقق منه تشغيل شامل:** `0e4975c428ecef502ccec023389262f1c0c1d868`، ونتائج GitHub Actions كلها **PASS**:
  - [Documentation governance](https://github.com/overurdream-collab/test2/actions/runs/39056206396): 6 tests + فحص Commit واحد ذري ومقارنة التاريخ القديم.
  - [G1–G7](https://github.com/overurdream-collab/test2/actions/runs/39056206455): PASS.
  - [G8](https://github.com/overurdream-collab/test2/actions/runs/39056206389): PASS.
  - [G9](https://github.com/overurdream-collab/test2/actions/runs/39056206433): PASS.
  - [Enterprise workspaces](https://github.com/overurdream-collab/test2/actions/runs/39056206457): PASS.
- **تنبيه:** تحديث هذا السجل/الحالة لاحق لتثبيت الأدلة فقط؛ يُختبر Commit التوثيق الجديد في CI مستقلاً ولا ينقل صلاحية إنتاجية.

## أين نتوقف؟
المطور الجديد يفتح `README.md` ← `docs/DOCUMENTATION_GOVERNANCE_AR.md` ← هذا الملف ← `docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md` ← `docs/MCIAS_V2_ACCEPTANCE_MATRIX_AR.md` ← تعليمات Codex، ثم يراجع الشيفرة على PR #22.

## الخطوة التالية المحددة
1. إثبات CI الجديد للفحص الآلي، وإضافة رابط تشغيله إلى حدث جديد في سجل التنفيذ.
2. **خطوة إدارة GitHub المطلوبة للتفعيل الكامل:** من المستودع افتح Settings → Rules → Rulesets (أو Settings → Branches حسب الواجهة)، وأنشئ/عدّل قاعدة على `main` تُلزم Pull Requests ونجاح فحص `Documentation governance / enforce` قبل الدمج، مع منع التجاوز غير المفوض. لم أتمكن من قراءة إعدادات الحماية بسبب `403 Resource not accessible by integration`، لذلك لا أزعم تفعيلها.
3. مواصلة Contract Intelligence والـTyped Rule Compiler عبر PR مستقل بعد تعريف صلاحيات وتوقيع المؤسسة، مع اختبارات على بيانات اصطناعية.
4. بعد مراجعة PR #22 والتصريح بالدمج، يسلم Codex الوكيل A1 وفق المعمارية ومصفوفة قبوله، ولا ينتقل إلى A2 قبله.

## معلومات التسليم
- مالك القرار: صاحب المشروع؛ المراجع الفني: هذه المحادثة المرجعية.
- مصدر قواعد البنود والأسعار: عقود المؤسسة وملاحقها المعتمدة بتاريخ الخدمة، لا تفسير AI.
- تعليمات التنفيذ: `docs/CODEX_MCIAS_V2_EXECUTION_HANDOFF.md`.
- ملخص التقنيات: FastAPI/SQLAlchemy/Alembic/PostgreSQL، واجهات enterprise ES modules، GitHub Actions.
- لا تُنسب نتيجة الاختبار إلى Commit غير مختبر؛ عندما تستكمل الخطوة التالية حدّث هذا الملف وسجل التنفيذ **في Commit نفسه**.


## Contract Intelligence sub-branch — Research R0 (2026-10-17)
- Child branch: feat/mcias-contract-intelligence from b694a2a1603a9a4c6d7af26ed56035b1a28b0166 (PR #22 remains draft/unmerged). This sub-branch research commit documents comparison of 6 external tools, model choices and native pypdf/Tesseract smoke tests; no production code or schema changes in R0.
- Research evidence: docs/CONTRACT_INTELLIGENCE_OPEN_SOURCE_RESEARCH_AR.md; decision CID-001–004; test report and architecture/handoff. No real Qwen inference, no Arabic OCR comparative evaluation, no CI for this exact new commit at author time: PENDING_CI.
- Existing G2 imports and ReferencePoint still work as baseline claimed by earlier PR22 CI; no assertion of success at this new SHA until CI verified.
- Next task: create actual source-anchored candidate extractor/validator with synthetic tests after research, then local LLM inference with version capture; keep proposals draft-only. No A1, merge, deployment or G3/G5 modifications.
- Resume: git switch feat/mcias-contract-intelligence; read CONTRACT_INTELLIGENCE_HANDOFF_AR.md and DG-001; every next commit updates this section and journal atomically.

### Contract Intelligence C1 — evidence gate (commit following R0)
- Added isolated pure advisory evidence validator and local-only OpenAI-compatible HTTP transport, NOT connected to API, UI, database or ReaderAgent yet. Every response remains DRAFT_ONLY. No model weights/runtime installed, real inference NOT_RUN. Unit tests and CI on this commit PENDING_CI.
- Files: mcias/contract_intelligence.py, tests/test_contract_intelligence.py; no migration/G3/G5 changes.
- Next: inspect exact GitHub CI at HEAD, fix tests, then connect G2 persisted source records under RBAC and add draft-only proposal persistence; do not activate financial rules.

### Contract C2: permissioned non-persistent preview
- PR #23 adds POST /api/v1/contract-intelligence/documents/{document_id}/preview and a source-ID preview button within existing reference points UI, plus 7 synthetic API tests and local inference redirect prevention. Existing G2 + SHA + user/field permissions reused, no new tables or financial mutations.
- The local OpenAI-compatible endpoint MUST be set by operator (MCIAS_CONTRACT_LLM_URL numeric 127.0.0.1:port path /v1/chat/completions, MCIAS_CONTRACT_LLM_MODEL, MCIAS_CONTRACT_LLM_REVISION) on private on-prem server. No model is connected in CI; API success tests mock inference, not real LLM.
- **NOT COMPLETE:** real Qwen inference, persistent candidates and approval UI, long PDF/tables/Arabic accuracy gold, typed compiler + institutional signature. Actual CI of this commit PENDING_CI; test failures to be documented/fixed in new commit.

### C2 adverse-test fix / HANDOFF-007
- On C2 SHA 1d84f576ea75c5632c8d2686c2c8d00021c75212: Governance Actions 39059261519 PASS, G9 Actions 39059261517 PASS, G1–G7 Actions 39059261540 FAIL (unit: 1 failed 389 passed 20 skipped); root cause LLM returned list as provider_code, causing TypeError in evidence validator. PostgreSQL job and dependency audit passed. C2 not marked fully passing.
- This fix checks invalid provider/service types safely, and requires numeric value inside the actual quoted clause, not elsewhere on same page. New SHA CI PENDING_CI. Next: inspect new CI. No real Qwen, no production activation.

### Contract C4 real synthetic files
- Added tests/test_contract_documents.py: exercises existing G2 on PDF native 2 pages (source page indices), XLSX three providers H1/H2/H3 with rows, OCR-disabled scanned PDF quarantine, and a prompt-bearing PDF treated as untrusted data. New SHA CI PENDING_CI; earlier C3 f1586d401e49577f767ef72d70237eda0f36973d G1–G7/G9/DG passed. No model inference or accuracy measurement; typed rule compiler still NOT IMPLEMENTED. Do not merge.

### C5 typed diagnostic compiler
- Added mcias/contract_rule_compiler.py (new SHA CI PENDING_CI). Only approved source-anchored tariff/copay references convert to inert typed AST with fingerprint; comparisons to supplied G3/G5 values report CONSISTENT/CONFLICT/NOT_APPLICABLE/INDETERMINATE, not deductions or payment decisions. No signed execution authority, no production activation and no integration into G5. No real model inference. Next verify exact CI and move to real LLM benchmark/proposal review.


### C6 Contract Intelligence — append-only proposal review (new SHA PENDING_CI)
- Child Draft PR #23 remains unmerged and targets PR #22 branch. C6 adds migration 0020 and immutable tenant-bound candidate/review/promotion tables. Endpoints: POST /api/v1/contract-intelligence/documents/{id}/extract (server-side evidence-checked model + persistence), GET /documents/{id}/proposals, POST /proposals/{id}/review and /promote. Independent reviewer decision is final; accepted complete source can be promoted to ReferencePoint **draft only**, never approved/executed.
- Exact earlier tested SHA 47996ebb937cca26b434747cf0450f7b07f41d75: governance 39060103800 PASS, G1–G7 39060103822 PASS, G9 39060103912 PASS, workspace 39060103888 PASS. C6 is PENDING_CI until its new SHA Actions checked.
- NOT_DONE: live pretrained Qwen inference, Arabic mixed/scan accuracy benchmark with ground truth, end-user review UAT, all acceptance cases, institution-bound cryptographic authorizations and production approval. Any unclear dates/OCR require review; no external patient data or commercial hosting.
- Immediate resume: inspect latest PR23 HEAD, exact CI, tests/test_contract_intelligence_api.py and migration 0020. Run isolated PostgreSQL and fix failures before another functional change, logging DG-001 at every commit. No merge/main/A1.


### C6 CI regression and C7 repair (2026-10-17)
- C6 SHA 88ec7edb50a1eb51156fe20470c550518f919d0a is **FAILED**: DG PASS run 39062436942; G1–G7 FAIL run 39062436975, G9 FAIL run 39062436968, Workspace FAIL run 39062436946. Root causes: five new synthetic tests had fixture 401 invalid session for new router, and migrations assert prior 0019 while additive schema is now 0020.
- New fix updates synthetic fixture auth only and replaces expected migration head with actual 0020 in PostgreSQL/G9 checks. Production permission checks are unchanged. Tests on new SHA PENDING_CI.
- No real Qwen inference, no proven Arabic clause metrics, no full reviewer browser UAT. No production activation, G3/G5 tariff replacement, main merge or A1. Next inspect exact CI of fix.


### C8: RTL reviewer UI and real-Qwen synthetic CPU benchmark — PENDING_CI
- Last fully tested contract branch SHA b161ee75076910f4f535d783d7adccc2c0d0d48e: all 5 Actions workflows PASS (see HANDOFF-012). New C8 UI lets permitted operators save AI candidates and independent reviewers inspect, accept/reject and promote only to ReferencePoint draft. No production financial activation.
- Added pinned Qwen/Qwen3-0.6B CPU-only GitHub Actions benchmark: 4 public synthetic cases (Arabic, English, mixed, prompt injection) with response hashes and measured TP/FP/FN, Precision/Recall, FPR. Weight/model SHA c1899de289a04d12100db370d81485cdf75e47ca (Apache-2.0). Script and workflow committed with no model weights, secrets or patient data.
- PENDING_CI on latest SHA. **Real inference not yet claimed**: test only counts after GitHub Actions actually runs and reports generated output. Production on-prem LLM remains not configured; 4-fixture benchmark is inadequate to certify provider prices/OCR. Still no signed approvals/merge/deploy or A1.


### C8 functional AI benchmark result / C9 diagnosis
- C8 SHA b20e5c2045d449c17ca3cc930efa0397bcea0ef9: ALL five regular GitHub workflows passed (Governance 39063356625, G1-G7 39063356576, G8 39063356628, G9 39063356604, Enterprise 39063356580). Real Qwen3-0.6B benchmark https://github.com/overurdream-collab/test2/actions/runs/39063356685 generated 4 actual local CPU completions; total 90.7 seconds, TP=0 FP=0 FN=3, Recall 0%, Precision undefined, all four cases ContractExtractionError, no extracted candidates. **MODEL GENERATION WORKS; CONTRACT EXTRACTION FAILS.** Do not mark Contract Intelligence complete.
- C9 now adds synthetic generated-response previews and negative gate on Recall=0, so infrastructure success cannot mask functional failure. New SHA PENDING_CI. Next investigate exact model completions/prompt, run another pinned real-model experiment; keep source validator strict, no production/patient data.


### C10 — constrained generation and PostgreSQL guard validation (PENDING_CI)
- C9 exact SHA daa4b934f84fd2e7bfefa0ed4de298b8c5178f0a intentionally failed the real pretrained Qwen3-0.6B benchmark run 39063739175: 4 local generated responses, fenced JSON top-level arrays and incorrect names/medical context, 0 valid proposals, TP0 FP0 FN3, Recall0%, Precision undefined. The prompt-injection pseudo-contract remained untrusted and rejected.
- C10 uses official noamgat/lm-format-enforcer v0.11.2 MIT **test harness only** to honor JSON format with source validation unchanged, tighter generic prompt, new PostgreSQL trigger negative regression on candidate+review+promotion history and regular CI inclusion. New exact SHA PENDING_CI.
- The 5 regular CI workflows at C9 SHA must be inspected independently. No 20+ gold documents and production-bound Qwen service/signatures, no production/merge/A1. Next: check actual benchmark outputs, Precision/Recall, DB test and docs CI; fix and log every failure.


### C10 exact CI FAIL / C11 syntax repair
- C10 SHA 19907cd2d06464769f1816e29aadac374c161e6a failed normal CI and pretrained model run because prompt example had invalid Python quote escaping (SyntaxError at contract_intelligence.py:237). This is a reproducible source regression, not model accuracy. Governance https://github.com/overurdream-collab/test2/actions/runs/39064329849 PASS; G1–G7 https://github.com/overurdream-collab/test2/actions/runs/39064329834 FAIL; Qwen https://github.com/overurdream-collab/test2/actions/runs/39064329875 FAIL before inference. G8/G9 also failed. C11 fixes literal escaping. New SHA CI PENDING_CI.
- Never claim real model C10 TP/FP/FN. Last valid measured model is C9 recall0. Remaining model-constrained actual test, PostgreSQL triggers and larger Arabic/OCR gold, signed institutional authorization; no main merge/production/A1.


### C12 Contract AI comparative pinned Qwen3-1.7B (PENDING_CI)
- Pre-C12 real-model C11 at SHA bee37b2df08f827c4e9fe53af604c064f8c0c808: https://github.com/overurdream-collab/test2/actions/runs/39064533187 FAIL, actual constrained JSON outputs all {"clauses":[]}; TP0 FP0 FN3, recall 0%, precision undefined. Syntax was correct, extraction did not work. Standard G1–G9 and DG checks reported successful at time of C12 initiation; do not equate them with AI pass.
- C12 changes ONLY the SYN CPU benchmark to pinned Qwen/Qwen3-1.7B revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e under Apache-2.0. Same 4 gold cases, LM Format Enforcer, source/numeric checks. Expected ~4GB weights, might exceed free runner limit; exact C12 CI PENDING.
- Remaining: real extracted source-backed clause quality acceptance, 20+ Arabic/English/mixed scanned contracts+provider XLSX gold, on-prem serving, independent human/tenant/browser/UAT and institution-signed activation. Never merge, deploy, operate on PHI, start A1 or activate finance.


### C12 measured result / C13 30-case synthetic evidence battery (2026-10-17)
- At C12 exact SHA d33c245251d956e98de7c582c75a95fc8a372735, Qwen/Qwen3-1.7B revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e loaded and generated four real outputs on synthetic-only standard CPU CI. Every response was empty `{"clauses":[]}`; TP0 FP0 FN3, recall 0%, precision undefined. Contract AI workflow https://github.com/overurdream-collab/test2/actions/runs/39064879988 **FAIL**. No model quality approval.
- C12 regular Governance 39064879959, G1–G7 39064879976, G8 39064879963, G9 39064879978 PASS. Enterprise 39064879967 FAIL: rate limit test expected 429 but observed 200 once within combined browser suite; requested exact-job rerun, cause not yet determined.
- C13 adds 20 quoted SYN clauses covering all 8 sections and 10 adversarial mutations. This is a deterministic validator regression suite, not extraction predictions or estimated accuracy. New SHA CI PENDING. No source/historical G3/G5/audit/approval changes, no main merge/deployment/A1. Next: inspect new CI and rerun, isolate rate limiting and run grounded AI model experiments against larger gold corpus.


### C14 — forced-nonempty SYN model diagnostic only (PENDING_CI)
- Pre-C14 latest tested deterministic C13 SHA 8726d7fa4fbf195f76b54bed8e07bc696c17a244: G1–G7 39065318369 PASS (438 passed, 21 skipped), G8 39065318384 PASS, G9 39065318434 PASS, DG 39065318341 PASS. Enterprise and 1.7B repeat job still in progress when new change authored.
- C11 0.6B and C12 1.7B experiments with optional empty output both had real generation but zero accepted clauses; this cannot count as model readiness. C14 changes ONLY the **public SYN test harness** JSON schema to minItems=1 on all positive/negative sources, tags metric output as experimental, and fails if any verified false positive emerges. The production model, controls and safe source validator are unchanged.
- New C14 SHA Actions PENDING. Even nonzero TP in this diagnostic is NOT ordinary extraction precision/recall certification; a production model must choose when NOT to extract. Remaining 20+ mixed/scanned PDFs, model choice, on-prem privacy, institutional signatures, UAT, no deployment or A1.


### C15 strict effective date source verification — new SHA pending
- On the child Contract Intelligence Draft PR23, C15 requires PDF/image effective dates to be literally present in the exact model-quoted clause; a date somewhere else on the same page is not sufficient. For XLSX G2 row, dates may come from other cells only on the same row. Unsupported/unnormalized date references get `needs_human_review`, not effective rules.
- Added three positive/negative validator regression tests for unrelated-page date, legitimate same Excel row, and invented date. No G3/G5, migrations, financial approval or model endpoint changed. All C15 Actions including full PostgreSQL/browser are PENDING_CI; do not assert PASS.
- C14 prior SHA 4a599db8f4b79757b23a1948f4ad042235faa06d: DG 39065549697, G1–G7 39065549695, G8 39065549696, G9 39065549706 PASS; forced pretrained model and Enterprise pending during C15 authoring. No production model approval, privacy transfer or A1. Next: check exact SHA tests, record measured source-model results and continue 20+ real-file gold benchmark.


### C15 test regressions and C16 prompt decontamination — PENDING_CI
- C14 real Qwen3-1.7B forced-candidate benchmark https://github.com/overurdream-collab/test2/actions/runs/39065549717 FAIL with TP0 FP0 FN3: four proposals generated but every proposal copied provider/service identity P7:XRAY from fixed sample in system prompt; all quarantined by independent source validator. No production AI acceptance.
- C15 SHA b677f6ccb4fd4a10554dc261c813cfb89c91a04d CI: DG 39065759302 PASS, G1–G7 39065759298 FAIL with two test fixtures (old XLSX row omitted date and reviewer sample invented end date); G8 39065759371 PASS, G9 39065759314 PASS, Enterprise 39065759329 FAIL from same regression. Strict source-date rule remains binding.
- C16 replaces hardcoded prompt example with **schema descriptions only**, and updates synthetic XLSX source row and reviewer document quotation to support legitimate effective dates. Adds test preventing future sample-value contamination. Exact new SHA all CI and actual Qwen model retest PENDING, not proof of functional success. No main changes, merger, on-prem model activation or A1.


### C17 prompt regression-test syntax fix (PENDING_CI)
- C16 SHA c1de2fa2e9e26a2a9da695e6397cab8df8c418eb introduced a missing `]}` bracket in new synthetic local-response test, so G1–G7 unit CI run 39066030984 FAILED during collection with SyntaxError before checking the actual prompt. C17 fixes ONLY the test response list; no changes to actual model or financial rules. All C17 SHA CI PENDING.
- C16 real model benchmark and remaining CI results must be reviewed at actual SHAs; no automatic completed claim, no merge/production/A1.

### C17 measured model / C18 minute-boundary limiter-test fix (PENDING_CI)
- Exact C17 SHA 3ee1d648e530086b153354688377b48a37f76055: DG 39066166099 PASS; G1–G7 39066166064 PASS; G8 39066166028 PASS; G9 39066166072 PASS; Enterprise 39066166119 FAIL one rate-limit timing test; real pinned Qwen3-1.7B forced-nonempty diagnostic 39066166029 FAIL: four nonempty JSON proposals, ALL quarantined due wrong service/logical key or null amount, TP0 FP0 FN3, Recall0%, precision undefined. No model approval.
- C18 pinning 60-second rate-limit clock in test fixture only, so 101 sequential requests no longer cross a real minute rollover. Production middleware untouched. C18 CI PENDING; stronger real model/20+ actual-file gold/Arabic OCR/signatures still open. No merge, deployment or A1.

### C19 cross-clause tariff identity gate — PENDING_CI
- C19 strengthens model quote evidence for PDF/image: provider_code, service_code and currency must be found in the verbatim **same quoted clause**, not any other clause on the page. Excel values may be in separate cells of the exact same trusted G2 row. Adds tests with two hospitals of same price and two services/currencies on one PDF page.
- No signed financial rule changes or institutional acceptance, no automatic AI activation. C19 full CI pending. Previous pinned Qwen3-1.7B source-backed recall 0/3, all four source claims rejected. Resume on Draft PR23 exact SHA and test results. No merge or A1.

### C20 — 20 source-file parser regression corpus (PENDING_CI)
- New `tests/test_contract_real_files_corpus.py` generates and parses 20 separate actual SYN binary documents through existing G2: 10 three-page PDFs (contract/price/exclusion with page anchors), 5 XLSX (H1/H2/H3 scoped rows), 5 scanned image-only PDFs (OCR disabled: quarantine, never auto-accept). Nothing contains PHI. This is parser-source evidence only, **not** 20 model extractions or Arabic OCR accuracy measurement.
- C19 exact SHA ac32fda06730dcd4618041011aee153bd84d7c97 G1–G7, G8, G9, Enterprise, Governance workflows all PASS, separate real-Qwen benchmark still not accepted. C20 exact SHA PENDING_CI. Missing actual model Precision/Recall on 20 realistic files, Arabic/mixed OCR and signed institutional financial activation; no merge/production/A1.

### C21 test-only pretrained Qwen2.5-1.5B-Instruct comparison (PENDING_CI)
- C21 changes ONLY `scripts/contract_ai_benchmark.py` to official Apache-2.0 Qwen/Qwen2.5-1.5B-Instruct pinned revision 989aa7980e4cf806f80c7fef2b1adb7bc71aa306, ~3.09GB pretrained weights. Maintains existing four SYN cases, LM Format Enforcer/forced-nonempty *diagnostic* and independent quote/amount/provider/date safeguards. No new production or autonomous financial model. CI PENDING at new SHA.
- Prior Qwen3-1.7B model outputs remained four quarantined/Recall0. Neither model approved. Missing 20+ real-file LLM extraction metrics, Arabic OCR, on-prem privacy and institution-bound signed financial activation; Draft PR23 unmerged, A1 not started.

 
### C22 — verified resume from exact C21 SHA / bounded slow local CPU test (PENDING_CI)
- Latest branch checked before C22: `920ac469268e80e56574a7913c6812410428ea50`, Draft PR #23 is still unmerged child of Draft PR #22. Latest completed feature C20 real synthetic binary G2 reader tests: 10 3-page PDFs, five 3-provider XLSX files and five OCR-disabled scanned PDF quarantine cases. Plus 20 fixed quote/source validator cases and 10 adversarial mutations. These **are not real pretrained model accuracy metrics**.
- C21 SHA 920ac469: DG run 39067055785 PASS; G1–G7 run 39067055757 PASS (unit 464 passed, 21 skipped; PG/deps pass); G8 39067055751 PASS; G9 39067055808 PASS; Enterprise 39067055807 PASS (combined 484 passed, 1 skipped). Real pretrained Qwen2.5-1.5B-Instruct benchmark run 39067055754 FAIL: one English JSON completion in log, 60-second HTTP client deadline and BrokenPipe; TP0 FP0 FN3, Recall0, precision undefined; no validated clauses.
- C22 changes only the explicitly opted-in upper bound for loopback `infer_local(timeout=...)` to 180s, benchmark requests opt into 180; **production preview still uses unmodified default 30s** and no model is production configured. Test asserts 30/180 accepted, 0/181 blocked. CI on C22 new SHA PENDING; no real-model improvement claimed.
- Still missing: real model with reliable sourced clauses and independent measure on 20+ source files, Arabic scanned OCR verification, comprehensive historical/tenant browser UAT, institution signed authorization for finance. No G3/G5 mutation/production/merge/A1. Continue from latest head and exact CI, not outdated C21 instructions.

 
### C23 — DG-001 grammar correction after C22 failure (PENDING_CI)
- C22 exact SHA `df5cb1f919769a0d461a777c291725b87952dabf`: governance https://github.com/overurdream-collab/test2/actions/runs/39067815796 **FAIL** because title `### HANDOFF-20261017-026 — C22 ...` had optional description rejected by overly exact heading regex, even though all eight fields/Current State were in same commit. G8 39067815744 PASS; G9 39067815771 PASS; G1–G7 and Enterprise initially in progress and must be checked on their own exact SHA. Pretrained Qwen2.5 test 39067815748 was in progress when C23 started. Do not count model inference as success before receiving metrics.
- C23 makes a narrowly extended heading grammar `### HANDOFF-YYYYMMDD-NNN — optional descriptive title` while preserving **all eight required fields, same-commit documentation, strict malformed-heading rejection and all-history scan**. Adds separate positive+negative governance unit test and updates DG-001 explanation; no history rewrites or hidden whitelist. New SHA CI `PENDING_CI`.
- C22 inference change preserved production default 30s; free SYN CPU harness explicitly opts into bounded 180s. No signed finance/production model or G3/G5 changes. Current blocker still measured actual model validation, 20+ model-operated bilingual docs, Arabic OCR & UAT. PR23 and parent PR22 remain Draft, unmerged. No A1.


### C24 — 2026-10-18 bilingual sourced copay prompt (PENDING_CI)
- Baseline PR23 21e4f39694037871e00f9259b1e29407d9216633 (parent PR22 DRAFT/unmerged): DG/G1–G9/Enterprise plus real model-run workflows SUCCESS; actual pinned Qwen2.5 SYN forced-nonempty diagnostic 39068088874 accepted 1/3 (TP1 FP0 FN2), Arabic copay and H2 mixed source missed. This does NOT establish ordinary extraction accuracy.
- One functional instruction in `mcias/contract_intelligence.py`: identify explicitly quoted Arabic patient copay, copy numerical percentage source token only. Added mocked local HTTP prompt assertion in `tests/test_contract_intelligence.py`; validation, evidence, human review, finance and local endpoint unchanged. Exact new SHA CI PENDING_CI, actual accuracy NOT_MEASURED.
- Next: inspect new SHA six workflows and real generated outputs TP/FP/FN, then document first change result before another modification. No main, production, finance or A1.


### C24 exact-SHA verified outcomes (documentation closure, 2026-10-18)
- C24 SHA `a3123b93db394fd3c0b61edd1ee946adcfe8a79a`: ALL six GitHub workflow families PASS, links in HANDOFF-20261018-002. Real pretrained Qwen2.5-1.5B-Instruct generated 4 SYN outputs and had TP1 FP0 FN2 / Precision100% on 1 accepted / Recall33.3%, unchanged from previous C23 diagnostic. 3 other outputs quarantined. Arabic amount `20%` not valid decimal; mixed logical_key `H2:H2_CONSULT` mismatches H2:CONSULT; injected negative quarantined. No automatic finance or production evidence.
- C24 bilingual prompt-only change did NOT improve observed extraction recall. Documentation closure new SHA CI PENDING_CI; model benchmark on closure SHA is not re-measured unless run, and C24 SHA is the measured evidence. Next single iteration should focus on schema-constrained numeric representation *without* relaxing validator; investigate options and run the same real benchmark/security tests. PR23/PR22 stay draft/unmerged.


### C25 — 2026-10-18 decimal-string constrained Qwen benchmark (PENDING_CI)
- C24 `a3123b93db394fd3c0b61edd1ee946adcfe8a79a` had six PASS workflows, actual Qwen forced SYN diagnostic TP1 FP0 FN2. Arabic copay generated `20%`, mixed H2 generated invalid `H2:H2_CONSULT`; both quarantined. C24 evidence recorded in docs-only `d81a78790b11e23e7b866973d1b80b4347461d83`; no evidence of improved model accuracy.
- C25 adjusts **only** the pinned LM Format Enforcer benchmark `amount` schema to require a decimal string (or null), plus synthetic static schema test. No independent evidence gate or production API changed. New SHA CI and actual model outcome PENDING_CI. Next action: inspect exact new run, not infer quality from successful model loading or schema test. No merge, finance, A1 or production.


### C25 actual evaluated — no model quality gain (2026-10-18)
- C25 SHA `caeec0d63c4dc75aa08ae5271ac55683450f6346`: all six Actions PASS (governance, G1–G9, Enterprise, pretrained Qwen synthetic benchmark). Actual Qwen generated TP1 FP0 FN2, recall33.3%, precision100% on one accepted source clause, 3/4 quarantined, one negative-case verified FP0. Model still generated Arabic `20%` rather than `20`, and mixed key `H2:H2_CONSULT` rather than `H2:CONSULT`. The C25 experimental JSON-schema pattern did not fix these outputs; **NO_IMPROVEMENT**, not production quality. Model run https://github.com/overurdream-collab/test2/actions/runs/39072778324. Evidence-only documentation closure new CI PENDING_CI.
- Next precise task: verify constrained parser runtime enforcement of string pattern with nullable union and reproduce with focused runtime test before modifying extraction again. Preserve all validator/finance/reviewer protections.


### C26 — runtime probe pending
- C25 schema remains unchanged. Added `tests/test_contract_lmfe_runtime.py` and dedicated no-model GitHub workflow pinned to LM Format Enforcer 0.11.2 to test whether C25 decimal regex rejects `20%` and accepts `20`, plus nullable branch. Previous SHA ee8c1f906dc4b3f73f56ecdc5595cc7d20568cda general CI passed, new probe actual CI PENDING_CI. No new model metrics, financial activation or reviewer changes. Next: read probe result before modifying schema.


### C26 harness correction PENDING_CI
- No-model runtime probe at dc8d03a69b843f1eb661859b6d2f65cce5c7a161 did not reach parser: pytest imported global `tests/conftest.py` with SQLAlchemy unavailable in isolated runner (Actions 39073517388 FAIL). Workflow now runs `--noconftest` to isolate dedicated schema test. Actual LMFE pattern result pending on new SHA; application/schema unchanged.


### C26 isolated runtime test — ASCII fixture pending
- No-model pinned LMFE run 39073594944 reached parser but rejected Arabic quote at character 49 before checking amount. Fixed test fixture ONLY to ASCII text for the amount-pattern investigation. This does not establish Arabic parsing quality; new SHA exact CI pending. No schema/application changes.


### C26 confirmed runtime nullable regex bypass / attempted anyOf fix (PENDING_CI)
- Pinned LMFE 0.11.2 no-model runtime run 39073665424 accepted `20%` with C25 `type=[string,null]` + `pattern`. This is a genuine constraint bypass for the tested schema, unlike prior harness failures. One SYN benchmark-only fix switches to explicit `anyOf` patterned string/null and updates tests, keeping source validation unchanged. New exact-SHA CI PENDING_CI; no production model or inference improvement asserted.


### C27 — isolate optional LMFE import from regular pytest (PENDING_CI)
- C26 SHA c9ea45e950bf480b75b929694f9621e807037e7a dedicated LMFE 0.11.2 runtime passed 20, 20%, null checks; G1-G7 and Enterprise broke at test import because optional library absent (runs 39073747367, 39073747397). C27 switches module import to `pytest.importorskip`, allowing normal suites to skip optional parser test while the dedicated job still installs LMFE and must execute it. No engine/schema/security/finance changes; latest CI PENDING_CI. Next: verify exact results and C26 actual Qwen metrics.


### C28 — safe derivation of verified tariff logical_key (PENDING_CI)
- C27 baseline 9287f9f3cf6aeec0a6fd132d113830d42180c347: all 7 workflow groups PASS, Qwen real SYN diagnostic https://github.com/overurdream-collab/test2/actions/runs/39074039943 generated TP2 FP0 FN1 (recall 66.7%; precision 100% among two verified positives), English H1 and Arabic copay verified; mixed H2 returned provider H2, service CONSULT, amount 7000.00, but wrong logical_key H2:H2_CONSULT. Forced-nonempty benchmark is not normal extraction quality.
- One source-validator change rebuilds malformed redundant tariff key as provider:service only when no other error exists except the key mismatch and provider/service and amount/date/quote are verified. No acceptance of unverified codes. Tests added for good H2 and wrong provider, wrong service, unsupported price/quote. New exact-SHA CI/real Qwen pending. No financial activation.


### C28 correction after CI failure (PENDING_CI)
- C28 827a73a2464b5c1f91aaa5c594bfdfa19315291b G1–G7 FAIL 1 negative gold case: wrong logical_key `H1:XRAY` was too broadly rewritten. Restrict deterministic repair to `provider:provider_service`, independent source checks fully valid, and add explicit negative test. New exact-SHA CI pending. Previous failure retained, no G3/G5 changes.


### C28 exact-SHA verified closure — 2026-10-18
- Exact functional SHA `01bf3711dff0a24e48c608c1c4372a6a851915bc` all 7 workflow groups completed SUCCESS: DG-001 https://github.com/overurdream-collab/test2/actions/runs/39075091215; LMFE parser https://github.com/overurdream-collab/test2/actions/runs/39075091171; G1–G7 https://github.com/overurdream-collab/test2/actions/runs/39075091259; G8 https://github.com/overurdream-collab/test2/actions/runs/39075091157; G9 https://github.com/overurdream-collab/test2/actions/runs/39075091197; Enterprise https://github.com/overurdream-collab/test2/actions/runs/39075091219; real pretrained Qwen https://github.com/overurdream-collab/test2/actions/runs/39075091291.
- G1–G7 unit exact log: 471 passed, 22 skipped, zero failed; previous adversarial `wrong_key` test no longer fails, and its H1:XRAY case remains rejected under the narrow correction.
- Actual 4 generated Qwen candidates: TP3 FP0 FN0, precision100%, recall100% only on 3 positive synthetic clauses; negative FPR0/1, 1 quarantined injected proposal, 129.4 total seconds. H1:CONSULT 5000 verified, Arabic copay_percent 20 verified, mixed H2 generated raw logical_key `H2:H2_CONSULT` but final verified prediction H2:CONSULT 7000 after safely canonicalizing exact redundant prefix. Injected transfer text quarantined. This test uses forced-nonempty diagnostic grammar (including negative); not a production selection/accuracy guarantee.
- All functional CI success and source-anchored SYN metrics verified. Only documentation changed in closure commit, whose own CI PENDING_CI. No merge/production/finance. Next resume from latest draft PR23 HEAD, retain conservative evidence gate.


### C29 Decimal benchmark scoring correction — pending new CI
- C28 exact documentation SHA `6fc0ad41493a6b5ccd102b84550507dba238619b` all seven Actions PASS including Qwen https://github.com/overurdream-collab/test2/actions/runs/39075390846. Real pretrained synthetic model run reported TP=2 FP=1 FN=1 / precision=66.7% recall=66.7%, with 4 candidates, 1 quarantined (negative injection), 0 source-verified false positives on 1 negative. Per-case: H1 TP1, Arabic copay TP1, H2 gold (tariffs,H2:CONSULT,7000) vs *source-verified* predicted (tariffs,H2:CONSULT,7000.00) recorded FP1 FN1 solely because original benchmark compared Python sets of raw strings. Recomputed from those actual recorded scored triples using Decimal semantic value: TP3 FP0 FN0 / precision100% recall100%, quarantined1 unchanged. This is corrected accounting of same original inference, NOT a new Qwen run or a new observed extraction improvement. Forced-nonempty tiny SYN benchmark not production validation.
- C29 replaces raw textual equality in `scripts/contract_ai_benchmark.py` with isolated Decimal-equivalent scoring, keeping exact section and logical key. Adds negative 7001/wrong-provider/wrong-service and historical raw-output recomputation tests. New SHA CI PENDING_CI; no change to model outputs or authoritative validation/finance.


### C30 script import environment fix (new SHA PENDING_CI)
- C29 functional SHA `cf7c26d2f688f6e6524e33686f3f6572d109b8f4`: seven original CI families except real Qwen passed, including Decimal test, DG-001, LMFE, G1–G9 and Enterprise. Qwen run https://github.com/overurdream-collab/test2/actions/runs/39076416659 FAILED before inference, traceback `ModuleNotFoundError: No module named 'scripts'` from `python scripts/contract_ai_benchmark.py` direct execution. Python sets sys.path[0] to scripts/, not repository root. New C30 changes just benchmark scorer import to `from contract_benchmark_scoring import count_matches`; existing test module still imports `scripts.contract_benchmark_scoring` from project-root pytest as before. Added no-model script-path import smoke under the dedicated Decimal CI, and retained the actual real CPU Qwen benchmark workflow to test complete startup. No model/gates/scoring changes.
- No new Qwen metrics at commit time; all C30 tests pending. Do not conflate historical C28 metrics with C29 startup failure. Draft PR23, no production/financial activation.


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


## DG-001 — توثيق ذري مطابق لعقد الحوكمة (20 أكتوبر 2026)
- مصدر الاختبارات الأصلي: PR #23 عند SHA `39a4a9b93e9eb04ea7c09c8c155c3e08f38c6ec0`، وليس SHA التوثيق الذري الجديد.
- آخر تشغيلات المصدر المكتملة: G1–G7 #39142051829، G8 #39142051813، G9 #39142051863، Enterprise #39142051799، DG #39142051833، LMFE #39142051800، Decimal #39142051864: جميعها PASS ضمن بواباتها.
- نماذج Qwen الاصطناعية: تشغيل source-specific #39142051770 TP3/FP0/FN0، بينما المستقل #39142051801 وC33 #39142051824 ينتجان TP2/FP0/FN4، Recall=33.33%. نجاح Workflow لا يساوي قبول جودة الاستخراج.
- PR23 يبقى DRAFT / NO INTEGRATION / NO PROD; تعارض Alembic مع سلسلة PR25 0019_input_clauses و0020_manual_contract_metadata موثق في تقرير DG-001 للقراءة فقط، بلا ترحيل.
- التحديث توثيقي فقط؛ إغلاق CI للـSHA الجديد مرهون بنتائج Actions على SHA الجديد دون نقل نتائج السابق إليه.
