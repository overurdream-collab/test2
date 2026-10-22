# E5 — ربط نتائج التدقيق بالتقرير القائم في G7

الحالة: **IMPLEMENTED / ISOLATED VERIFIED** ضمن اختبارات الإسقاط المحددة أدناه. اختبار المسار النهائي على PostgreSQL 16 وCI والقبول المستقل لدى المشرف؛ لا اعتماد إنتاجي أو قرار مالي.

نقطة الاستئناف: `ba1ec6bdb578eaefa19920985fddfbcc8bede945`. تفويض المشرف حصر العمل في G7 واختباراته، بعد قراءة عقد المخرجات وCAI-01. لم تُعدّل ملفات G3 أوG5 أوShared Audit أوالترحيلات، ولم يُنشأ سجل أو محرك موازٍ.

## ما تغير

- بقيت `create_snapshot(db, actor, batch_id)` واجهة الخدمة القائمة، وبقي `state/held/approved/payable` مستقلًا عن نتيجة التدقيق. النتيجة الاستشارية لا تسمح بالصرف أو الرفض الآلي.
- يحفظ dataset بالإصدار2، مع `audit_state` الرسمي بالإصدار2، ونسخة الحالة الأصلية، وسبب معتمد إن كان موجودًا، و`completed_audit`، وتغطية الفحوص والشهادات، ومعرفات المصدر وموضعه وG5 وShared Audit وG6. تستعمل القراءة القديمة `project_audit_findings` دون تعديل JSON التاريخي أو اختراع سبب.
- يعرض `summary.audit` عدادات الحالات الأربع، والمكتمل وغير المكتمل، وعدد السجلات دون حالة مسجلة `unclassified_count`، وشهادات المرجعيات المكتملة/المطلوبة، ومصادر المطالبات المثبتة. `unclassified_count` عداد نقص داخل غير المكتمل، وليس حالة تدقيق خامسة.
- يتطلب الاكتمال MATCH_VERIFIED أوVIOLATION_PROVEN؛ ثمانية فحوص فعلية مكتملة وقواعد مطابقة لمعرفاتها ونسخ موجبة؛ ست شهادات معتمدة مكتملة وسارية بتاريخ الخدمة والتغطية؛ مصدرًا مطابقًا لسجل المطالبة ومستند الدفعة وSHA واعتماد النطاق؛ وحدث Shared Audit واحدًا مطابقًا للحالة ونسختها وسببها والمطالبة والمصدر والمرجعيات. نقص نافذة التاريخ الذي يحجب فحص G5 يمنع الاكتمال. المخالفة تحتاج أيضًا finding مخالفة محفوظًا.
- يبقى outcome الأصلي ظاهرًا إذا غاب حدث التدقيق، مع `completed_audit=false`. يحجب التقرير عند تناقض الحدث أو تعدده لنفس snapshot. لا تُعاد كتابة النتيجة لتلبية القبول.
- تمر المرجعيات عبر `claim_reference_projection` ثم `clean_claim_audit_details`، مع تواريخ effective/coverage منظمة من الشهادات المحفوظة. لا تُنسخ `records` أوقيم المستفيدين. معرفات أدلة القواعد UUID canonical فقط؛ النص غير المؤهل لا يعرض ويمنع وصف اكتمال الفحص. gaps/evidence IDs المخالفة لعقد Shared Audit تحجب بإجابة عامة دون إعادة النص الحساس.
- يتيح explorer مرشح `audit_state` مع صلاحياته المؤسسية القائمة. يضيف XLSX/PDF العربي والإنجليزي ملخص النتائج؛ يظل التصدير الافتراضي تجميعيًا بلا معرف مستفيد أو تفاصيل مصدر خام، والتصدير الأصلي يخضع لصلاحياته السابقة.
- يستخدم حدث `g7_report_frozen` الكاتب المشترك `write_event`، مع `version` فقط. يربط `resource_type=report_snapshot/resource_id` النسخة التي تحمل البصمة؛ لا حقل SHA حر خارج عقد الكاتب. يمنع fingerprint نفسه إنشاء نسخة أو حدث جديدين عند الاستئناف، ويُسلسل قفل الدفعة نسخ PG16.

## التحقق الفعلي وحدوده

1. قبل تشديد المراجعة: اختبارات pure وG7 السابقة وقراءة explorer والتصدير غير HTTP: **35 PASS /7 deselected، 2.24s**. الاختبار الأول للمسار الفعلي على SQLite: **4 PASS /14 deselected، 32.24s** للأربع حالات، مع G2 Excel/CLAIMS دون PAYMENT وG4 وG3 وG5 وShared Audit وG6 وG7 وإعادة القراءة بعد Commit والعزل والنسخ. هذه الأرقام لا تثبت تشديد الحدث اللاحق.
2. أثبتت المراجعة المستقلة غياب شرط الحدث؛ اختبار `test_completed_audit_requires_durable_shared_audit_correlation` كان **RED:1 FAILED، 0.23s** قبل الإصلاح، لأن `completed_audit` كان True دون حدث.
3. بعد التشديد والتنقية: `pytest -q tests/test_g7_inputs_first_reporting.py -k 'not native_services'`: **30 PASS /4 deselected، 0.41s**. تشمل الأربعة outcomes، missing/duplicate/conflicting event، الحالة/نسختها/نسخة المرجع، قواعد بلا نسخة أو بنسخة سالبة أو معرف غير مطابق، انتهاء السريان، عدم تطابق مستند الدفعة، وحالات PHI holdout داخل rule.reference وcertificate.gaps/evidence_ids، ومنها legacy، وحفظ المصدر التاريخي والتصدير الآمن. ثم أضيف شرط نوع الحدث `claim_entry` ونتيجته `success` بملاحظة المراجع، ومرشح `conflicting_shared_audit or four_outcomes or requires_durable` نجح **14 PASS /22 deselected، 0.41s**، ومنه اختبارا mutation الجديدان. لا تُجمع الأعداد المتداخلة بوصفها اختبارات مستقلة.
4. `tests/test_g7_web.py` لدى المشرف في السياق المسموح: **8 PASS، 0.68s**؛ XML `/tmp/g7-web-root.xml`. محليًا علق TestClient قبل الاستجابة؛ stack أظهر انتظار AnyIO portal/futures/selector، ولم يثبت سبب النظام نفسه. أوقفت العملية والمحاولة التشخيصية المحدودة ولم أغير اختبارًا أو سياسة شبكة. لم يتكرر التعليق لدى المشرف.
5. `git diff --check` ناجح. لا تشغيل PG أوشبكة من وكيل G7. اختبار native النهائي جاهز في `tests/test_g7_inputs_first_reporting.py` بمرشح `native_services`؛ يستخدم fixture الخدمات القائمة ويفرض PG16 إذا زُود بـ`MCIAS_TEST_DATABASE_URL`. حالة match تختبر إنشاء التقرير نفسه متزامنًا من جلستين، ثم retry وإعادة الاستيراد ونسخة G6 لاحقة وحفظ القديمة. الثلاث الأخرى تثبت VIOLATION/UNRESOLVED/AUDIT_UNAVAILABLE دون تحويل مالي. اختبارات الترحيل والحاجز الفيزيائي القائمة لم تتغير.

يمكن للمشرف ضبط `MCIAS_G7_EVIDENCE_OUTPUT` إلى ملف JSONL لحفظ أحداث ومعرفات وبصمات وملخصات الحالات native دون سجل المرجعية الخام. لم يُنشأ رابط CI أوartifact متخيل؛ تشغيل PG وCI على Commit النهائي ثم تحديث هذا الدليل من اختصاص المشرف.

## المتبقي

مراجعة contract_quality المستقلة بالقراءة أغلقت ملاحظاتها، دون تشغيل اختبارات إضافية من المراجع. بصمة الملف المراجع `mcias/reporting_g7.py`: `4abb1e6d55acc82e25577aaa66215c3a2e9910f0aeb3753d1882cf671719f9be`، وبصمة الاختبار: `9bf2bb9841a7f1c43d6d1700e0b6b1611ba3dff1b5c0748b3edda87018ba598b`.

المشرف: PG16 النهائي على Commit هذا التسليم، وCI مطابق، ثم قرار القبول المخول؛ وتسجيل الدليل وإغلاق نطاق E5 فقط. الأداء وجودة OCR والعقود والحكم المالي والقبول الإنتاجي خارج نطاق هذا التغيير، ولا يُستدل عليها بأعداد الاختبارات. المصدر المشترك المرجعي هو سجل التدقيق القائم، ولا دمج أو نشر أوforce push أوبيانات مرضى حقيقية.

## HANDOFF-20261022-502 — المؤشرات الأربعة وتصنيفات العرض الخمسة

الحالة: **IMPLEMENTED / ISOLATED VERIFIED** للإسقاط والاختبارات المملوكة فقط. الأساس `df849b96efc0741eca8157c77e08b1a67fed2b16`، وملفات G7 كانت نظيفة ومطابقة للتجميع وفق استلام المشرف. لا ادعاء PG/CI جديد في هذا التعديل.

اعتمد المشرف واجهة إضافية `summary.dashboard` بإصدار1؛ لا تغيير في `summary.audit` أوحالات G5 أوالقيم المالية السابقة. الواجهة النهائية:

```json
{
  "schema_version": 1,
  "kpis": {
    "total_claimed": {"by_currency": {"USD": {"status": "KNOWN", "amount": "120", "missing_amount_count": 0}}},
    "audited_claims": {"count": 1, "by_currency": {"USD": 1}},
    "review_required": {"claim_count": 1, "finding_count": 1, "by_currency": {"USD": {"claim_count": 1, "finding_count": 1}}},
    "potential_exposure": {"by_currency": {"USD": {"status": "UNQUANTIFIED", "amount": null, "unquantified_claim_count": 1}}}
  },
  "classification_counts": {
    "NO_DETECTED_FINDINGS": 0,
    "HUMAN_REVIEW_REQUIRED": 1,
    "MISSING_EVIDENCE": 0,
    "UNABLE_TO_AUDIT": 0,
    "HUMAN_APPROVED_REJECTION": 0
  },
  "recommended_rejection_pending": {"available": false, "claim_count": 0, "reason_code": "APPROVED_REJECTION_POLICY_UNAVAILABLE"},
  "human_approved_rejected": {"claim_count": 0, "claimed_by_currency": {"USD": "0"}}
}
```

هذا مثال واجهة، لا نتيجة مطالبة حقيقية. يضيف الصف وallowlist الـexplorer: `audit_classification, financial_decision_status, review_finding_count, decision_event_id` فقط. لم تُعدّل UI أوharness أوDocker أومسار تشغيل G5؛ يستهلكها المشرف ضمن ملكيته.

- التصنيف إسقاط قراءة واحد لكل مطالبة: رفض G6 بشري صالح مع `completed_audit` → `HUMAN_APPROVED_REJECTION`؛ ثم التعذر/غياب نتيجة موثوقة → `UNABLE_TO_AUDIT`؛ ثم نقص الفحوص/الأدلة → `MISSING_EVIDENCE`؛ ثم الملاحظات/الاعتراض المفتوح → `HUMAN_REVIEW_REQUIRED`؛ وإلا اكتمال دون ملاحظات → `NO_DETECTED_FINDINGS`. مجموع عدادات الخمس يساوي المطالبات الفريدة؛ تبقى الحالات الأربع نفسها دون enum أوخدمة جديدة.
- قراءة الرفض تستند إلى الحدث المحفوظ في G6 للمطالبة واللقطة المختارتين: هوية actor/event/opener UUID، وقت وسبب منظم، اقتراح/حجز سابق، وفصل صاحب القرار عن المفتتح والمقترح وصاحب الحدث السابق وفق الخدمة القائمة. لا تفويض أوكتابة قرار من G7، ولا إعادة بناء نظام الصلاحيات. إلغاء القرار باعتراض أحدث أوصدور snapshot أحدث يمنع توريث الرفض القديم.
- `financial_decision_status=REJECTED` يعرض حدث G6 المؤهل مستقلاً؛ إذا كان التدقيق ناقصًا تبقى فئة `MISSING_EVIDENCE`/`UNABLE_TO_AUDIT` ولا يُحسب ضمن `human_approved_rejected`. الاعتماد المالي الموجود لا يحول تدقيقًا ناقصًا إلى سليم. قيم `state/payable/deduction` القديمة لم تتغير.
- KPI المراجعة يجمع `HUMAN_REVIEW_REQUIRED` و`MISSING_EVIDENCE`؛ `UNABLE_TO_AUDIT` منفصل في توزيعه. عدد findings هو النتائج غير المطابقة ذات قاعدة/نسخة مؤهلتين، مع الاعتراض المفتوح؛ لا يُخترع finding لغياب snapshot. علامة `human_review_required=True` الاستشارية عند MATCH لا تصبح ملاحظة.
- تحفظ المبالغ Decimal وتفصل العملات. إجمالي المطالب به يستعمل تسوية الدفعة القائمة مرة واحدة؛ حواجزها ما زالت تحجب الدفعة/المبلغ/العملة غير الصالحة بدل إصدار صفر أوتقرير غير متسق. `KNOWN/missing_amount_count=0` لا يدعي تغطية صفوف غير مستوردة.
- لا يتوفر عقد موثوق لـaffected intervals أواتحادها؛ لذلك كل تصنيف غير `NO_DETECTED_FINDINGS` يبقى تعرضه `UNQUANTIFIED/amount=null`، حتى الرفض البشري. الصفر للـNO_DETECTED_FINDINGS ضمن نطاق فحوصه المكتملة فقط؛ ليس ضمان غياب كل خطر. `claimed_by_currency` قيمة المطالبات المصنفة رفضًا، وليست تعرضًا أووفورات أوخصمًا محققًا. حقول affected_amount أوrejection_policy المقترحة من caller لا تنشئ سلطة مالية.
- سياسة رفض فوري معتمدة وسارية غير موجودة في العقد الحالي؛ يبقى المؤشر `available=false/claim_count=0` وسببه صريحًا، دون اختراع مبلغ توصية أوإنشاء سياسة.

التحقق الفعلي بعد هذا التغيير:

- `pytest -q tests/test_g7_inputs_first_reporting.py -k 'dashboard or redacted_explorer'`: **14 PASS /35 deselected، 0.41s**؛ خمس فئات حصرية وأربع KPIs، عملتان، تعدد الملاحظات دون مضاعفة المطالبة، رفض بشري مكتمل/ناقص/غير مؤهل، اعتراض لاحق ونسخة أحدث، exposure مجهول رغم فرق مالي مثبت، غياب سلطة الرفض، ورفض مؤسسة أخرى، وحقول explorer المنقاة.
- `pytest -q tests/test_g7_reporting.py tests/test_g7_inputs_first_reporting.py -k 'not native_services and not dashboard and not redacted_explorer'`: **47 PASS /18 deselected، 0.32s**؛ انحدار G7 للمصدر والتسوية والخصوصية والأربع نتائج وشروط اكتمال الحدث. لا تشغيل G2/G3/G5 baseline واسع ولا PG أوشبكة من هذا المالك.
- `git diff --check`: ناجح. يحتاج المشرف تشغيل PG16/HTTP/UI وCI على Commit التجميع النهائي، ثم القبول المستقل. بيانات الاختبار اصطناعية، ولا merge/reset/force/deploy أوإعادة كتابة لقطات قديمة.
