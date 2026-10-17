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
