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
