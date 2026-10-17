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
