# MCIAS v2.0 — سجل التنفيذ والمراجعة وقابلية استلام المشروع

**المستودع:** https://github.com/overurdream-collab/test2  
**الفرع:** `feat/temporal-reference-inputs-and-four-outcomes`  
**Draft PR:** https://github.com/overurdream-collab/test2/pull/22  
**مرجع الوكلاء:** https://github.com/overurdream-collab/test2/pull/19  
**تاريخ بدء هذه الدفعة:** 17 أكتوبر 2026  
**تصنيف:** تطوير واختبار بمصادر اصطناعية؛ غير معتمد لإنتاج المطالبات الطبية.  
**من يقرأه:** مدير المشروع، مطور جديد، Codex، مراقب الجودة، المراجع الأمني والمؤسسي.

## 1. ماذا طُلب، وما التعريف الدقيق للإنجاز؟

طلب صاحب المشروع الحفاظ على **المداخل المتخصصة** بدل قائمة خدمات عامة، مع إمكانية استيراد وثيقة وإضافة/تعديل النقاط وتاريخ فتح وإغلاق كل بند، وأن تكون التعرفة مختلفة لكل مقدم خدمة، وأن تختار المطالبة شرطها بتاريخ الخدمة. المطلوب أيضًا أن تكون مخرجات التدقيق أربعة ملفات: مرفوض بمخالفة قطعية، مقبول بعد الفحص، مرفقات ناقصة، مراجعة بشرية.

**الأولويات:** الحفاظ على G3/G5/Palermo والعقود الموقعة؛ منع الحذف والسجلات المزورة؛ اختبار قبل الدمج؛ توثيق ما تم وما لم يتم دون ادعاء.

**حد الإنجاز الحالي:** سجل بنود زمني قابل للاختبار + شاشة أولية + **توفيق قراءة فقط** مع G3/G5 + إرفاق الأدلة بلقطة التدقيق + أربعة ملفات CSV مراجعة. **ليس** استخراج AI من الملفات أو اعتماد تلقائي لجميع قواعد المؤسسة أو تشغيلًا إنتاجيًا.

## 2. سجل العمليات بالترتيب (خطوة / ملفات / تعديل / إثبات)

| رقم | الخطوة المنفذة | الملفات المحددة | أثرها | اختبار أو دليل |
|---|---|---|---|---|
| E00 | جرد G3 وG5 وPalermo والواجهة وعدم إعادة بنائها | `models_reference`, `reference`, `audit_agents`, `audit_service`, `palermo2`, `web_workspace` | تثبيت الأساس وقيوده | قراءة المستودع، مراجعة CI على main |
| E01 | فرع محمي ومسودة PR #22 | فرع `feat/temporal-reference-inputs-and-four-outcomes` | عدم تغيير main أو الإنتاج | سجل Commit/PR |
| E02 | نموذج بنود زمنية وإغلاق append-only | `models_reference_points.py` | لا تعديل محتوى البند بعد اعتماده | `test_temporal_point_persistence.py` |
| E03 | ترحيل قاعدة البيانات وحواجز PostgreSQL | `alembic/versions/0019_reference_points.py` | تهيئة الجداول وحماية من تعديل/حذف | PostgreSQL CI |
| E04 | خدمة إضافة/تعديل/اعتماد البنود | `reference_points.py` | شروط التاريخ، نطاق المؤسسة، Decimal، وثائق المصدر، فصل المهام | اختبارات تواريخ ورفض المسودات |
| E05 | API للصلاحيات والنطاق | `reference_points_api.py` | read/write/approve واختبارات 403/404 | `test_reference_points_http_security.py` |
| E06 | مخرجات تدقيق أربعة أصناف حصرية | `claim_outcomes.py`, `claim_outcomes_api.py` | قراءة لقطات التدقيق، CSV آمن، منع احتساب مطالبة مرتين | `test_reference_points_and_outcomes.py` |
| E07 | شكل مدخلات جديد (كل قسم) | `reference_points_view.js`, `views.js`, `workspace.css` | ملف/بند/تعديل وتواريخ وإصدارات بالعربية والإنجليزية | واجهة المؤسسة/المتصفح، تحتاج UAT |
| E08 | عرض الملفات الأربعة | `audit_outcomes_view.js`, `views.js` | ملخص وCSV لكل حالة لدفعة مطالبات | اختبار API وCI |
| E09 | تحديث G9 بعد 0019 | `preflight_g9.py`, `release_g9.py`, اختبارات migration | معالجة تضارب head السابق 0018 vs 0019 | G9 Actions |
| E10 | تثبيت تاريخ الأسعار والعرض Decimal | `reference_points.py`, واختبارات PostgreSQL | تصفية بالتاريخ قبل pagination، إظهار 4 منازل عشرية | فحص حدود وخط انحدار |
| E11 | تشديد معنى الرفض القطعي | `claim_outcomes.py` | لا رفض دون فشل موثق + Palermo مستقل | التصنيف الرباعي |
| E12 | ربط المرجع الزمني بمسار التدقيق الفعلي | `reference_rule_bridge.py`, `audit_agents.py` | G3/G5 مرجع مالي، بند جديد لا يستبدله؛ أي تعارض HOLD | `test_reference_rule_bridge.py`, `test_g5_agent_order.py` |
| E13 | حفظ أثر المرجع الزمني في التدقيق والتقارير | `audit_service.py`, `claim_outcomes.py` | معرفات البنود وإصداراتها وتاريخها وبصماتها في لقطة غير قابلة للتعديل؛ CSV `reference_versions` | اختبارات G5 وCSV |
| E14 | اختبارات HTTP وعزل المؤسسات | `test_reference_points_http_security.py` | منع مستخدم للقراءة من الكتابة أو رؤية مؤسسة ثانية | CI G1–G7 |
| E15 | ضبط التصنيف عند وجود بند معتمد غير مفسر | `claim_outcomes.py`, `test_reference_points_and_outcomes.py` | لا تتخطّى تقارير `HUMAN_REVIEW` التناقض | اختبار negative |
| E16 | إنشاء مرجع المطور ومصفوفة قبول | `MCIAS_V2_DEVELOPER_START_HERE_AR.md`, `MCIAS_V2_ACCEPTANCE_MATRIX_AR.md`, هذا الملف | يُمكن الاستلام من GitHub دون قراءة سجل محادثة | مراجعة الوثائق عبر PR |
| E17 | اختبار تكامل G5 الموقع فعليًا | `tests/test_g5_agent_order.py` | policy حتمي موقع اصطناعيًا + مرجع موافقات غير مفسر → `AuditSnapshot.calculation.status=held` وPalermo held وHUMAN_REVIEW | `test_run_audit_immutable_snapshot_captures_reference_block` |
| E18 | حماية PostgreSQL من إدراج معتمد بالقوة | `0019_reference_points.py` | أول إدخال لا بد أن يكون `draft`، حتى لو تجاوز ORM | اختبار `test_reference_points_postgres.py` |
| E19 | اختبار SQL مباشر أمام الـtrigger | `tests/test_reference_points_postgres.py` | يحاول INSERT approved وUPDATE وDELETE ثم يثبت بقاء الأصل | PostgreSQL CI |
| E20 | تسليم مواصفة مرحلة الذكاء التعاقدي | `MCIAS_CONTRACT_INTELLIGENCE_AND_RULE_COMPILER_SPEC_AR.md` | مواصفة مفصلة للتنفيذ الآمن دون ادعاء أن المستخرج AI يعمل | مراجعة بنود المواصفة |
| E21 | تعليمات تسليم Codex والمراجعين | `CODEX_MCIAS_V2_EXECUTION_HANDOFF.md` | ترتيب القراءة، حدود الأمان، المهام المفتوحة، وقف الادعاء بالاكتمال | رابط README |
| E22 | فهرسة كل الوثائق من المستودع | `README.md` | لا يحتاج المطور إلى هذه المحادثة لمعرفة الهيكل والاختبارات وحالة التنفيذ | روابط docs وPR |



### حوادث اختبار تم إصلاحها أثناء التطوير
- أول CI بعد migration فشل لأن فحوص G9 وG5/G6/G7 القديمة كانت مثبتة على `0018_claim_query_indexes`; حُدّثت إلى `0019_reference_points`. هذه مشكلة توقع نسخة، لا مشكلة في عقد المستخدم.
- اختبار SQLite أعاد القيمة `5000` بدل `5000.0000` في تمثيل السلسلة؛ وُحّد تنسيق الحقول المالية للإخراج إلى أربع منازل دون استعمال float.
- فحص Enterprise G8 PostgreSQL احتوى توقع head قديم؛ صُحّح وأُعيد تشغيل CI.
- اكتشاف حدّ pagination: التصفية بتاريخ الخدمة يجب أن تسبق `limit/offset`. صُحّحت وحُددت حدود مقبولة.
- فحص ملف `REJECTED_RULE_CERTAIN`: لا يكفي أن يدّعي الوكيل `fail_confirmed` ما لم تكن حالة Palermo `verified`; جرى حجب التصنيف القاطع عند غياب هذا الإثبات.

## 3. الأدلة الآلية المثبتة على قاعدة الكود قبل آخر وثائق التسليم

النسخة `4d9f689623ac25511df9ba8b8aa2fc8057a6fb5f` (وتشمل جسر البنود، ربطه بـG5، اختبار الاعتماد الموقع والحماية على PostgreSQL) اجتازت:
- [G1–G7](https://github.com/overurdream-collab/test2/actions/runs/39054804583): **success**.
- [G8](https://github.com/overurdream-collab/test2/actions/runs/39054804495): **success**.
- [G9](https://github.com/overurdream-collab/test2/actions/runs/39054804532): **success**.
- [Enterprise workspaces/browser](https://github.com/overurdream-collab/test2/actions/runs/39054804546): **success**.

**ملحوظة:** هذه النتائج تخص SHA المبين أعلاه. أُضيفت بعدها ملفات توثيق وربط README دون تغييرات وظيفية؛ يجب فحص CI لآخر SHA قبل الدمج. لا تمثل الاختبارات تصريح تشغيل إنتاجي.

## 3.1 الأدلة الآلية السابقة التي تحققت بالفعل

قبل دمج جسر القواعد الأخير، نجحت على نسخة PR #22 السابقة SHA `b4db3781a040b4c62ad67ac689de79ac0d8430f6` أربع مجموعات:
- G1–G7: https://github.com/overurdream-collab/test2/actions/runs/39051386987
- G8: https://github.com/overurdream-collab/test2/actions/runs/39051387049
- G9: https://github.com/overurdream-collab/test2/actions/runs/39051394728
- واجهة المؤسسة: https://github.com/overurdream-collab/test2/actions/runs/39051385438

**هذا إثبات للنسخة السابقة فقط**. لا يُعاد نسبه تلقائيًا إلى أحدث SHA بعد تغييرات الكود. سجّل لاحقًا في نهاية هذا الملف آخر SHA ونتائج جميع اختبارات أحدث commit.

## 4. القرارات الأمنية غير القابلة للتفاوض

1. لا كتابة مباشرة على المطالبات الأصلية، ولا تعديل `AuditSnapshot`، ولا حذف `ReferencePoint` أو `ReferencePointClosure`.
2. `ReferencePoint` الجديد **ليس بديلًا** عن `ContractVersion`, `ProviderTariff`, `AuditPolicyGrant`. أي اختلاف → HOLD.
3. استخدام `service_date` وليس `imported_at` لفحص السريان. الفترات `[from, until)` لا تتداخل.
4. عزل المؤسسة: كل جدول/استعلام/API يربط `organization_id` وصلاحية مستخدم، و`provider_code` عند اختيار التعرفة.
5. لا تخمين للغة عقد، لا رفض مالي تلقائي ولا اتهام أو استنتاج سريري من نموذج AI.
6. الاعتماد يحتاج فصلًا بين مدخل البند ومراجعه وتفويض مؤسسة؛ **في الإنتاج ما زال ربط التوقيع ببصمة البند غير منفذ وبالتالي التفعيل معطّل**.
7. CSV يحتمل قيمًا خبيثة من مصدر المطالبة؛ نمنع Excel formula injection ولا نصدر أسماء المرضى افتراضيًا.

## 5. النواقص المعلّمة — لا تضع عليها علامة «نجح» قبل إصلاحها

- **L1 — Contract Intelligence:** OCR/LLM يقرأ PDF/Word/Excel ويقدم مسودات بنود مع مصدر الصفحة/الصف/التفسير والثقة، ويطلب اعتمادًا منفصلًا. الموجود حاليًا رفع ملف فقط، وليس استخراجًا تعاقديًا آليًا.
- **L2 — Policy compiler:** تنفيذ نوعي صريح لكل بند (الشبكة، الاستثناء، الفئة، الموافقات، حد التغطية، عدد المستفيدين، السقوف)، مع صيغة شرط معتمدة ومرجع أسبقية؛ الإشارات غير المدعومة `HOLD`.
- **L3 — Authorization:** توقيع مؤسسي مرتبط ببصمة البند نفسه وحالة مراجعة مستقلة، ثم UAT لموافقة السوبر أدمن بعد الصلاحيات المكتوبة.
- **L4 — G3 tariff lifecycle:** توحيد استبدال تعرفة العقد المالي الموقع مع النسخ المؤرخة أو مسار تحويل معتمد؛ لا يفعل PR #22 ذلك، بل يكتشف التناقض فقط.
- **L5 — Complete beneficiary roster:** تعريف وإثبات اكتمال قائمة المستفيدين ضمن التاريخ والشركة والفئة قبل الجزم بعدم الأهلية. لا تقارن «عدم العثور» بـ«الرفض القطعي».
- **L6 — Certain rejection verification:** بناء تحقق مستقل لفشل حتمي بنوعه وأدلته دون الاعتماد على كلام النموذج؛ Palermo اليوم يُعلّق أي فشل في الفاحصين الثمانية.
- **L7 — Human and financial decisions:** اختبار G6 واقعي بمحاكاة اعتراض وإعادة تدقيق، والمبالغ المرتجعة/الموفرة دون احتساب مزدوج.
- **L8 — Production:** تقييم أمن وخصوصية وأداء ونسخ احتياطي رسمي وفحص اختراق وموافقة مؤسسة قبل أي تشغيل بيانات حقيقية.
- **L9 — A1–A5:** تطوير مستقل؛ ممنوع نسب AI إلى محركات القواعد الحتمية.
- **L10 — Integration concurrency:** اختبار متزامن فعلي لمُعدّلَين مختلفين على نفس البند في PostgreSQL، وقياس الأداء والصفحات الطويلة؛ لا يكتفي باختبار SQLite منفرد.

## 6. تسلسل العمل الآمن للمرحلة التالية

(1) تثبيت CI لآخر SHA + معالجة أي فشل حقيقي.  
(2) مراجعة صلاحيات UI + اختبار موظف القراءة وسوبر أدمن ومراجع مستقل وطلبات غير مصرح بها.  
(3) تنفيذ **مترجم عقد Typed** مشروط بالسياسة وليس استخراج LLM مباشر للتفعيل.  
(4) عقد تفويض موقع بالبصمة وتعريف قواعد الأسبقية وتحديث G3/G5 بتوافق رسمي.  
(5) بناء إثبات كامل لسجل الأهلية والتحقق المستقل من فشل القواعد قبل تفعيل «رفض قطعي».  
(6) تطوير A1 في فرع مستقل ثم قياس Precision/Recall/False Positives على بيانات اصطناعية.  
(7) مراجعة رسمية مستقلة PR، ثم موافقة صاحب المشروع على الدمج، دون نشر/إنفاق تلقائي.

## 7. قاعدة التوثيق عند كل تغيير مستقبلي

أضف سطرًا جديدًا إلى جدول E00–En لهذه الخطوة: **الهدف، الملف، التغيير، السلوك، السيناريو الموجب والسالب، رابط Commit SHA، رابط GitHub Actions، حالة الاعتماد**. حدّث `MCIAS_V2_DEVELOPER_START_HERE_AR.md` و`MCIAS_V2_ACCEPTANCE_MATRIX_AR.md` إذا تغيرت وظيفة أو تم إغلاق فجوة. يحتفظ GitHub بتاريخ commits، لكن هذا السجل يفسر **لماذا** تغير السلوك وما الذي يثبت صحته. لا تدمج حالة «النجاح الهندسي» مع «الاعتماد المؤسسي».


### HANDOFF-20261017-001
- Scope: إنشاء سياسة توثيق DG-001 وإلزام كل تغيير جديد بسجل تنفيذ ونقطة استئناف محدثة، وإضافة فحص CI وقالب PR وفهرسة من README؛ لا تعديل في محرك المطالبات.
- Why: طلب صاحب المشروع سياسة دائمة لكل حفظ أو تعديل لتسليم المشروع لأي مبرمج أو Codex دون فقدان السياق أو سوء تفسير حالة التطوير.
- Files: docs/DOCUMENTATION_GOVERNANCE_AR.md; docs/MCIAS_V2_CURRENT_STATE_AR.md; docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md; scripts/check_documentation_governance.py; tests/test_documentation_governance.py; .github/workflows/documentation-governance.yml; .github/PULL_REQUEST_TEMPLATE.md; README.md; docs/CODEX_MCIAS_V2_EXECUTION_HANDOFF.md.
- Tests: python -m unittest tests/test_documentation_governance.py ; python scripts/check_documentation_governance.py --base b69defa2f621458ef44d790b510840307a81009a --head HEAD --legacy-cutoff 8bdb43fd467f5766ecaa8cbc48f379dea99e17cb ; GitHub Actions CI for exact HEAD.
- Result: PENDING_CI — لم تصدر نتيجة الاختبارات الجديدة عند كتابة هذا الحدث؛ لا يُنقل نجاح سابق إليه.
- Risks: الفحص الآلي يحكم على محتوى Commit بعد إرساله، ولا يمنع دمجًا إن لم يُضف إلى Required Checks في إعدادات حماية main؛ تطبيق الإلزام التاريخي يبدأ بعد Legacy Cutoff ولا يمحو Commits السابقة.
- Next: التحقق من GitHub Actions على Commit السياسة، وفحص حماية main ثم جعل حالة Documentation governance / enforce إلزامية بعد مراجعة الصلاحيات والموافقة المناسبة.
- Handoff: ابدأ من README ثم DG-001 ثم CURRENT STATE؛ كل Commit جديد يضيف حدث HANDOFF بالحقول الثمانية ويعدل CURRENT STATE معه في Commit ذري.


### HANDOFF-20261017-002
- Scope: تحسين آلية مقارنة فروع Pull Request عند تقدم main، ومعالجة انتهاء صلاحية SHA القديمة بعد squash، وإضافة اختبار محلي يتحقق من رفض Commit برمجي غير موثق وقبول Commit ذري موثق؛ تحديث روابط أول إثبات CI.
- Why: منع فشل كاذب عند تغير SHA أساس main، ومنع ادعاء أن حارس التوثيق فعّال دون اختبار سلبي فعلي.
- Files: scripts/check_documentation_governance.py; tests/test_documentation_governance.py; docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md; docs/MCIAS_V2_CURRENT_STATE_AR.md.
- Tests: python -m unittest discover -s tests -p test_documentation_governance.py -v; Documentation governance GitHub Actions and existing G1–G7/G8/G9/workspace suites on new SHA.
- Result: PENDING_CI — أول Commit d7009e6c اجتاز Governance https://github.com/overurdream-collab/test2/actions/runs/39055995211؛ هذا التعديل لم يختبر بعد وقت الحفظ.
- Risks: حماية main المطلوبة لإنفاذ النتيجة على الدمج لا تزال تحتاج تحقق صلاحيات وإعداد قواعد الحماية؛ الاختبار يفرض تسجيل السبب ولكنه لا يضمن صحة المحتوى دون مراجعة بشرية.
- Next: افحص CI على SHA الجديد ثم أضف إثبات نجاح مستقل، وفعّل Required Status Check عبر مسؤول المستودع إذا كان مخولًا.
- Handoff: اقرأ DG-001 ونقطة الحالة وسجل التنفيذ، واستخدم Commit ذري يضم الشيفرة وHANDOFF وCURRENT_STATE معًا؛ فشل الفحص يوقف قبول PR.


### HANDOFF-20261017-003
- Scope: تثبيت روابط نتائج CI الخمسة المؤكدة عند `0e4975c428ecef502ccec023389262f1c0c1d868` في سجل التنفيذ ونقطة الاستئناف؛ لا تغييرات وظيفية ولا تعديل للشيفرة.
- Why: سياسة DG-001 تلزم إثبات النتائج الفعلية وعدم ترك PENDING_CI بعد التأكد، حتى يميز أي مبرمج بين الاختبار الناجح والافتراض.
- Files: docs/MCIAS_V2_CURRENT_STATE_AR.md; docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md.
- Tests: GitHub Actions على `0e4975c428ecef502ccec023389262f1c0c1d868`: Documentation governance https://github.com/overurdream-collab/test2/actions/runs/39056206396; G1–G7 https://github.com/overurdream-collab/test2/actions/runs/39056206455; G8 https://github.com/overurdream-collab/test2/actions/runs/39056206389; G9 https://github.com/overurdream-collab/test2/actions/runs/39056206433; Enterprise https://github.com/overurdream-collab/test2/actions/runs/39056206457.
- Result: PASS على SHA `0e4975c428ecef502ccec023389262f1c0c1d868` في المجموعات الخمس؛ هذا Commit تثبيت الأدلة لم يُفحص بعد وقت الحفظ.
- Risks: سياق GitHub Actions ليس حماية دمج تلقائية ما لم تكن الحالة Required في Rulesets؛ الاتصال الحالي لا يملك إذن قراءة إعدادات branch protection (403)، ولا يوجد تصريح بأن main محمي.
- Next: مسؤول GitHub يفعّل Required Checks على main بعد مراجعة المسودة؛ المراجع الفني يتحقق من PR #22 ثم يقرر الدمج، دون تغييرات مالية إنتاجية.
- Handoff: ابدأ من README وDG-001 وCURRENT_STATE، واتبع تعليمات Codex. أفضل دليل ناجح مثبت هو SHA المذكور أعلاه، مع التمييز بينه وبين أي Commits لاحقة.


### HANDOFF-20261017-004
- Scope: Research First stage for Contract Intelligence. Created 5 dedicated documents on new child branch; compared 6 OSS tools, audited existing G2 source parser and ReferencePoint; no application code/migration/UI behavior changed.
- Why: User mandatory research before programming and DG-001 instant handoff; decisions CID-001 to CID-004.
- Files: docs/CONTRACT_INTELLIGENCE_OPEN_SOURCE_RESEARCH_AR.md; docs/CONTRACT_INTELLIGENCE_ARCHITECTURE_AR.md; docs/CONTRACT_INTELLIGENCE_TEST_REPORT_AR.md; docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md; docs/CONTRACT_INTELLIGENCE_DECISION_REGISTER_AR.md; docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md; docs/MCIAS_V2_CURRENT_STATE_AR.md.
- Tests: Local synthetic pypdf 2-page extraction; tesseract eng PNG; artifact_tool synthetic xlsx export. Commands + results described in CONTRACT_INTELLIGENCE_TEST_REPORT_AR.md. GitHub full pytest NOT_RUN due DNS preventing clone; third-party installs and real Qwen inference NOT_RUN.
- Result: PASS only three small independent local smoke probes; untested OSS and real inference NOT_RUN; CI on this specific Commit PENDING_CI.
- Risks: no Arabic OCR accuracy, no on-prem model runtime, no provenance-validation implementation. Licenses for model weights may restrict commercial deployment. GitHub report initially is not functional contract-agent delivery.
- Next: Implement synthetic corpus + quote/locator validator on feat/mcias-contract-intelligence, and log a new HANDOFF in same Commit; then run targeted tests and attach Actions evidence.
- Handoff: Open docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md; read DG-001 and CURRENT_STATE; preserve current PR #22 financial authority, no merge or A1.


### HANDOFF-20261017-005
- Scope: Added pure bounded Contract Intelligence anchor validator and local-only OpenAI-compatible model transport; synthetic unit tests. No endpoint, database migration, approved reference mutation, G3/G5 or AI-agent A1.
- Why: Following completed Research R0, implement minimum new MCIAS-specific evidence and typing gap; reuse G2 original locators and avoid parser rewrite; CID-001/002/003.
- Files: mcias/contract_intelligence.py; tests/test_contract_intelligence.py; docs/MCIAS_V2_CURRENT_STATE_AR.md; docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md; docs/MCIAS_V2_DEVELOPER_START_HERE_AR.md; docs/MCIAS_V2_ACCEPTANCE_MATRIX_AR.md; docs/CONTRACT_INTELLIGENCE_TEST_REPORT_AR.md; docs/CONTRACT_INTELLIGENCE_ARCHITECTURE_AR.md; docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md.
- Tests: python -m pytest -q tests/test_contract_intelligence.py (intended CI; not executed on this repo locally because git clone blocked by DNS). The unavailable runtime probe is an EXPECTED negative test, not real AI inference.
- Result: PENDING_CI / NOT_RUN local targeted repo test. No real Qwen execution and no measured extraction precision or recall.
- Risks: potential Python/CI regression pending test, parser may not carry granular text spans; model without explicit local runtime remains unavailable; unauthenticated use prohibited because module not exposed yet.
- Next: Verify GitHub Actions results on exact commit and repair any failure with new DG-001 event; then wire permissioned G2 document-only preview API.
- Handoff: inspect PR #23 HEAD, tests/test_contract_intelligence.py and module; run pytest with -q then follow docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md; do not merge.


### HANDOFF-20261017-006
- Scope: Added tenant/scoped source preview API and RTL/LTR button in existing reference points screen; harden localhost model transport against redirects and unhashable model output; add synthetic API/negative tests. No schema migration, proposal persistence, G3/G5/Palermo financial changes, deployment or A1.
- Why: Reuse existing G2/ReaderAgent/Palermo-1 and protect sensitive fields, prevent AI side effects; CID-001, CID-003; extend C1 after full G1-G7/governance success at SHA 453aebde6a8d349207331bbd0bd1b96c5bc34169.
- Files: mcias/contract_intelligence.py; mcias/contract_intelligence_api.py; mcias/app.py; mcias/web_workspace/reference_points_view.js; tests/test_contract_intelligence.py; tests/test_contract_intelligence_api.py; docs/MCIAS_V2_CURRENT_STATE_AR.md; docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md; docs/MCIAS_V2_DEVELOPER_START_HERE_AR.md; docs/MCIAS_V2_ACCEPTANCE_MATRIX_AR.md; docs/CONTRACT_INTELLIGENCE_TEST_REPORT_AR.md; docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md; docs/CONTRACT_INTELLIGENCE_ARCHITECTURE_AR.md.
- Tests: python -m pytest -q tests/test_contract_intelligence.py tests/test_contract_intelligence_api.py (CI run required); node --check mcias/web_workspace/reference_points_view.js (CI/workspace run required). C1 SHA 453aebde: Governance https://github.com/overurdream-collab/test2/actions/runs/39058718203 success; G1-G7 https://github.com/overurdream-collab/test2/actions/runs/39058718217 success.
- Result: PENDING_CI for this C2 SHA; mocked model tests are not model inference. Real LLM NOT_RUN.
- Risks: Source values treated untrusted and sensitive, strict `medical_fields.<field>.read` permission required; preview not persisted; unreviewed/uncertain OCR held; data may appear in permitted preview and must never be used for real payments. No original SourceFile modification.
- Next: Verify C2 exact SHA CI and regressions, fix fails in new atomic DG-001 commit, then implement signed/append-only proposal persistence with separate reviewer and real local LLM benchmark.
- Handoff: Fetch PR #23 HEAD, read api.py + tests and `CONTRACT_INTELLIGENCE_HANDOFF_AR.md`; run tests with synthetic DB; configure model only inside isolated private environment; never merge/deploy.


### HANDOFF-20261017-007
- Scope: Repair one adversarial model-output crash in Contract Intelligence validator; tighten numeric evidence to quoted clause not entire PDF page; regression test added. No schema/API authority change or G3/G5 financial change.
- Why: CI on C2 SHA 1d84f576ea75c5632c8d2686c2c8d00021c75212 failed 1 unit test with TypeError on list-valued provider_code (https://github.com/overurdream-collab/test2/actions/runs/39059261540). Also identified wrong-price-on-same-page false anchor. Fix fail-safe handling without weakening source evidence.
- Files: mcias/contract_intelligence.py; tests/test_contract_intelligence.py; docs/MCIAS_V2_CURRENT_STATE_AR.md; docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md; docs/CONTRACT_INTELLIGENCE_TEST_REPORT_AR.md; docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md.
- Tests: C2 GitHub Actions G1-G7 unit 1 failed / 389 passed / 20 skipped, PostgreSQL and dependency audit PASS. Governance run 39059261519 PASS; G9 run 39059261517 PASS. New test test_page_with_two_prices_cannot_anchor_wrong_price_to_other_clause added; on this fix commit no CI evidence yet.
- Result: C2 FAIL objectively; this fix PENDING_CI. Never attribute prior passes to new SHA.
- Risks: Local LLM unconfigured; quote precision in Arabic and OCR untested, malformed nested responses can remain problematic; human reviewer required. No historical version changes.
- Next: Check unit, PG, security, browser, governance actions on this exact head SHA; record results and implement remaining review/persistence only if green.
- Handoff: git switch feat/mcias-contract-intelligence; read test failure logs from 39059261540 and added adversarial tests; follow docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md; avoid A1, main and production.


### HANDOFF-20261017-008
- Scope: Added synthetic real-source G2 file reader integration tests: two-page PDF, XLSX three providers, scanned PDF without OCR quarantined, and instruction-bearing PDF treated as text. No model, API, database, G3/G5, rule or A1 changes.
- Why: Research-first R0 and C1-3 validated data shapes; this tests actual existing pypdf/openpyxl G2 source paths rather than faked extracted records.
- Files: tests/test_contract_documents.py; docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md; docs/MCIAS_V2_CURRENT_STATE_AR.md; docs/CONTRACT_INTELLIGENCE_TEST_REPORT_AR.md; docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md; docs/MCIAS_V2_ACCEPTANCE_MATRIX_AR.md.
- Tests: python -m pytest -q tests/test_contract_documents.py (new and not locally run in repository). Previous C3 commit f1586d401e49577f767ef72d70237eda0f36973d: GitHub Actions G1-G7 https://github.com/overurdream-collab/test2/actions/runs/39059432403 PASS, G9 https://github.com/overurdream-collab/test2/actions/runs/39059432394 PASS, Documentation governance https://github.com/overurdream-collab/test2/actions/runs/39059432745 PASS.
- Result: PENDING_CI for this new SHA; source parser tests are not real AI inference and not measured clause extraction accuracy.
- Risks: Arabic/OCR confidence, table layout and multi-file amendments untested; no persistent proposals, typed compiler or signed rule activation; missing model runtime.
- Next: Check exact SHA CI for G1-G9/browser/docs; fix regressions atomically, then proceed to typed diagnostic compiler and real local model benchmark.
- Handoff: See docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md, run tests/test_contract_documents.py and all CI on exact SHA; remain Draft PR #23, no merge.


### HANDOFF-20261017-009
- Scope: Add only inert typed diagnostic compiler for approved-source tariffs and copay with provenance/fingerprint, historic validity, tenant/provider/currency and explicit data mismatch. Test negative unknown/unsigned/forged terms. No integration into finance/Palermo audit execution, no database or A1.
- Why: Research R0 and CID-003: only whitelisted provable terms compile as non-executable diagnostic; ambiguous legal/medical terms blocked, source versions immutable. Reuse reference_rule_bridge for actual G3/G5 authority.
- Files: mcias/contract_rule_compiler.py; tests/test_contract_rule_compiler.py; docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md; docs/MCIAS_V2_CURRENT_STATE_AR.md; docs/MCIAS_V2_DEVELOPER_START_HERE_AR.md; docs/MCIAS_V2_ACCEPTANCE_MATRIX_AR.md; docs/CONTRACT_INTELLIGENCE_TEST_REPORT_AR.md; docs/CONTRACT_INTELLIGENCE_ARCHITECTURE_AR.md; docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md.
- Tests: python -m pytest -q tests/test_contract_rule_compiler.py (GitHub Actions expected); no local repo clone. Earlier C3 SHA f1586d4 governance and G1-G7/G9 passed; C4 SHA 39350aee CI must be checked separately.
- Result: PENDING_CI for this typed compiler commit, not a claimed pass; real Qwen inference NOT_RUN; precision/recall NOT_MEASURED.
- Risks: Caller-supplied financial reference values are NOT proof they are signed, so module never activates rules; signature-bound institutional authorization is missing. No production payment/rejection operations.
- Next: Inspect exact current SHA CI; record any failing test with a new DG-001 event; then benchmark real local model and implement proposal persistence and reviewer workflows.
- Handoff: Read typed compiler module/tests then Contract Intelligence handoff; keep financial G3/G5 bridge unchanged, no merge, no production.


### HANDOFF-20261017-010
- Scope: Add persistent immutable organization-scoped contract candidates, separate review event and optional promotion to reference DRAFT only, PostgreSQL migration 0020, API and synthetic tests. Existing G2, signed G3/G5, main, production and A1 remain unchanged.
- Why: C1–C5 preview did not persist extracted clauses or independently reviewed decisions. Reuse existing trusted G2 evidence / ReferencePoint; research CID-003/004.
- Files: mcias/models_contract_proposals.py; alembic/versions/0020_contract_proposals.py; mcias/contract_proposals_api.py; mcias/app.py; mcias/reference_points.py; alembic/env.py; tests/test_contract_intelligence_api.py; docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md; docs/MCIAS_V2_CURRENT_STATE_AR.md; docs/CONTRACT_INTELLIGENCE_TEST_REPORT_AR.md; docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md; docs/MCIAS_V2_DEVELOPER_START_HERE_AR.md; docs/MCIAS_V2_ACCEPTANCE_MATRIX_AR.md.
- Tests: python -m pytest -q tests/test_contract_intelligence_api.py tests/test_contract_intelligence.py tests/test_contract_rule_compiler.py tests/test_contract_documents.py (new tests submitted for GitHub Actions); Alembic PostgreSQL migration and all existing CI expected. No local repository clone because DNS fails.
- Result: PENDING_CI — no PASS claimed for new SHA. Prior head 47996ebb937cca26b434747cf0450f7b07f41d75 passed governance run 39060103800, G1–G7 run 39060103822, G9 run 39060103912, Enterprise run 39060103888.
- Risks: Real Qwen inference not run; synthetic HTTP tests mock the LLM. Model candidate text may still need medical/legal interpretation. Reviewer must independently inspect original source; no source fields copied in candidate JSON. PostgreSQL append-only triggers protect review history. Promotion cannot invent dates/automatic amendments or bypass written authorization. No institutional signature-bound production activation.
- Next: Check exact SHA CI and repair any G9/PostgreSQL/API regressions with fresh DG-001 event. Then browser review flow, real private inference, golden precision/recall and independent security/UAT review.
- Handoff: Use PR #23 child feat/mcias-contract-intelligence of PR #22. Run alembic upgrade head in isolated test PostgreSQL and listed tests. Review pending CI, never merge/activate. See Contract Intelligence handoff and DG-001.


### HANDOFF-20261017-011
- Scope: Repair C6 first-commit CI failures without altering signed financial rules. Patch synthetic API fixture to mock new proposal-router auth (production auth remains real); bump hardcoded Alembic head expectations 0019->0020 in G5/G6/G7/G8, PostgreSQL integration and restore, and G9 release/preflight.
- Why: At C6 SHA 88ec7edb50a1eb51156fe20470c550518f919d0a, Actions G1–G7 39062436975 FAIL (unit 5 new tests rejected with HTTP 401 invalid session; postgres 5 migration-head asserts). G9 39062436968 FAIL (migration head and restore). Enterprise 39062436946 FAIL (same plus G8 head). Governance 39062436942 PASS. Errors are evidenced in job logs; no success was attributed to C6.
- Files: tests/test_contract_intelligence_api.py; mcias/preflight_g9.py; mcias/release_g9.py; tests/test_postgres_integration.py; tests/test_restore_drill.py; tests/test_g5_postgres.py; tests/test_g6_postgres.py; tests/test_g7_postgres.py; tests/test_g8_postgres.py; docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md; docs/MCIAS_V2_CURRENT_STATE_AR.md; docs/CONTRACT_INTELLIGENCE_TEST_REPORT_AR.md; docs/CONTRACT_INTELLIGENCE_HANDOFF_AR.md.
- Tests: GitHub Actions previous exact SHA (see links above); new full pytest, PostgreSQL migration + G9 preflight and browser workflow on fix SHA queued after commit. NOT_RUN locally owing GitHub clone DNS.
- Result: Previous C6 FAIL; fix PENDING_CI. No pretrained Qwen inference or Arabic precision/recall tested.
- Risks: Other migration-head snapshots or additional actual API defects could emerge after fixture repair. Patching test expected head only follows an actual additive 0020 migration; financial G3/G5 validation remains immutable.
- Next: Verify next GitHub CI exact SHA and fix remaining runtime/test regressions; only then expand UI and real inference evaluation.
- Handoff: Continue Draft PR #23, inspect job failures and tests. Read current state and governance. Never merge, deploy or activate rules without separate authorization.
