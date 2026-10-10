# خطة الاختبارات الخارجية

معرّف الوثيقة: `MCIAS-EXT-001` · الإصدار: 1.0 · الحالة: مسودة للمراجعة · اللغة: العربية

[English version](EXTERNAL_TEST_PLAN_EN.md) · [فهرس الحزمة](ACCEPTANCE_PACK_INDEX.md)

## البداية والنطاق

الحالة الخارجية: **NOT_EXECUTED**. لا يُستورد نجاح CI كتوقيع قبول. يحدد قائد الاختبار الجهة وSHA وصور الحاويات/المكتبات والمضيف والشهادات وتاريخ التشغيل ومالك كل قاعدة. يبدأ الاختبار اصطناعيًا؛ أي بيانات حقيقية تحتاج إذن خصوصية وسياسة ونقل محلي منفصل. تقرير النتائج باستخدام [القالب](EXTERNAL_TEST_REPORT_TEMPLATE.md).

## شروط الدخول والتوقف

- سياسة نطاق الاختبار وأسماء المضيفين/الشبكات معتمدة، وخطة نسخ/استعادة ورجوع، وأدوار مشغّل ومراجع مستقل محددة.
- مصدر كامل مثبت وبصمات موثوقة، venv ومكتبات اختبار وNode/Chromium، عملاء PG16 على PATH، وقواعد اختبار منفصلة جديدة.
- لا يُشغّل restore/seed/reset أو regression على قاعدة قائمة. اختبارات الانحدار تحتاج حسابًا إداريًا اصطناعيًا لإنشاء أدوار وقاعدة الاستعادة؛ يختلف عن حساب التطبيق المحدود.
- توقف فور ظهور بيانات غير مصرح بها أو تسريب مفاتيح أو تغيير أصل/لقطة أو فساد/تعطل خارج النطاق. احفظ دليلًا منقحًا وأبلغ المخول، دون مواصلة محاولة هجومية.

## مراحل التنفيذ

| ID | المرحلة | التنفيذ/الدليل | القبول |
|---|---|---|---|
| EXT-01 | المصدر والحزمة | SHA مستقل، SHA256SUMS، مكتبات مثبتة | التطابق؛ لا مفاتيح أو بيانات في الحزمة |
| EXT-02 | الهدف | deploy_check test بحساب تشغيل محدود، ثم production-profile في بيئة معزولة | PASS هندسي للفحوص المنفذة؛ لا قبول إنتاجي |
| EXT-03 | الانحدار | Python + PG + restore + Node | لا فشل؛ تفسير كل skipped وتحذير |
| EXT-04 | Seed | تشغيلان على قاعدة seed مستقلة ومقارنة receipt | لا مضاعفة، ورفض قاعدة/بيئة غير مسموحة |
| EXT-05 | المتصفح | السكربتات الأربعة أدناه وصورها | RTL/LTR، الهاتف/اللوحي، السيناريوهات، دون أخطاء |
| EXT-06 | صلاحيات ومال | حالات T06/T07/T08/T11/T15/T20 والمراجعة المستقلة | الرفض من الخادم وبقاء الأصل واللقطات |
| EXT-07 | الأداء | EXPLAIN وخطة تزامن ومقاييس P95 على بيانات اصطناعية | وفق SLA مكتوب؛ دونه NOT_APPROVED |
| EXT-08 | الأرشفة | شهر به بيانات اصطناعية للمؤسسة ومؤسسة أخرى وnull actor | تشفير/قراءة/عزل وعدم حذف؛ توثيق المستثنى |
| EXT-09 | التعافي | DB+مصادر مشفرة ومفاتيح منفصلة في هدف جديد | البصمات والسجلات صحيحة وRPO/RTO مقاسان |
| EXT-10 | UAT والأمن | الخطط الثنائية المرفقة ونتائج العيوب | توقيع مستقل بعد الإغلاق، لا تحويل تلقائي لـACCEPTED |

## الانحدار مع PostgreSQL

```bash
# Protected session already holds separate synthetic administrative URLs.
export MCIAS_TEST_DATABASE_URL="$MCIAS_REGRESSION_DATABASE_URL"
python -m pytest -q
npm test
npm run check
python -m compileall -q mcias tests scripts
# A different freshly migrated *_e2e DB for the dedicated Seed test:
export MCIAS_E2E_DATABASE_URL="$MCIAS_SEED_DATABASE_URL"
export MCIAS_ENVIRONMENT=development
python -m mcias.seed --output .e2e-output/seed-check.json
export MCIAS_SEED_TEST_DATABASE_URL="$MCIAS_SEED_DATABASE_URL"
python -m pytest tests/seed -q
```

MCIAS_REGRESSION_DATABASE_URL وMCIAS_SEED_DATABASE_URL اسمان لجلسة المشغّل، لا Settings للتطبيق؛ يُمرران إلى المتغيرات المعروفة في الكود كما أعلاه. استخدم قاعدة seed أخرى، ولا تعاود الانحدار الكامل على قاعدة مستخدمة لأن fixtures موروثة لها مفاتيح ثابتة. تتضمن اختبارات T17 إنشاء/حذف قاعدة استعادة اصطناعية؛ هذا تعديل اختبار مقصود ومصرح، بخلاف deploy_check للقراءة فقط. إذا تخطى pytest اختبار Seed العام، يجب تشغيله منفصلًا وتوثيقه؛ لا تُهمل PostgreSQL أو الاستعادة بحجة أن suite خضراء.

## دورة المتصفح

جهّز MCIAS_STORAGE_DIR الخاص وMCIAS_STORAGE_KEY وMCIAS_MFA_ENCRYPTION_KEY الاصطناعيين في الجلسة قبل التشغيل؛ لا تطبع القيم ولا تستعمل قيم CI في الإنتاج.

```bash
# Fresh browser *_e2e database; protected environment supplied by operator.
export MCIAS_ENVIRONMENT=development
export MCIAS_ENABLE_UI_DEMO=true
export MCIAS_DATABASE_URL="$MCIAS_E2E_DATABASE_URL"
python scripts/seed_workspace_e2e.py
python -m uvicorn mcias.app:app --host 127.0.0.1 --port 8000 --no-access-log
# Second terminal inherits the SAME database, storage directory and keys:
python scripts/check_workspace_browser.py --base-url http://127.0.0.1:8000
python scripts/check_workspace_live.py --base-url http://127.0.0.1:8000
python scripts/check_integrated_workflow.py --base-url http://127.0.0.1:8000
python scripts/check_retention_browser.py --base-url http://127.0.0.1:8000
```

السكربت integrated_workflow يولد لقطة G5 من Python وPalermo-2 كـfixture؛ **ليس** API تشغيل إنتاجي. Seed العام metadata-only ولا يوفر ملفات أصل فعلية؛ دورة الرفع هي دليل حفظ الأصل. ملفات live-fixture.json وseed-check.json تحتوي بيانات دخول اصطناعية ولا تدخل التقرير المنشور.

## الأداء والتعافي وحدود القياس

في قاعدة أداء أخرى `_e2e`، `python -m mcias.seed --count 10000 --output .e2e-output/perf.json`، ثم `python scripts/benchmark_operational_indexes.py`. الفهارس الثلاثة أصبحت في الرأس الحالي، لذا قد يستخدمها before أيضًا؛ لقياس فرق قبل/بعد فعلي كرر على قاعدة أداء مستقلة مثبتة عند 0017، ولا تسقط فهارس التشغيل. الجداول الفارغة لا تثبت فائدة فهارس التدقيق/التقارير. `python -m mcias.performance_g9 --claims 1000 --repeats 3` اختبار حساب اصطناعي، لا SLA للـAPI. تحدد الجهة الحمل والتزامن/المدة ومقاييس latency وCPU/IO وسعة الأقراص قبل التجربة؛ اختبار إغراق الشبكة ليس ضمنها تلقائيًا.

الاستعادة حسب G9_DISASTER_RECOVERY_AR.md، والمقارنة بأعداد وجداول وبصمات أصل ولقطات، لا بمجرد استجابة health. الأرشفة محدودة وتستثني null actor؛ تطبيق legal holds/purge أو stream كبير عمل لاحق محجوب، فلا تُسجل PASS له.

## الإغلاق والأدلة

لكل EXT يسجل المراجع SHA والأمر المنقح والوقت UTC والبيئة/نوع البيانات والمقاييس والنتيجة والدليل والعيب. تحفظ النتائج الأصلية داخليًا وتُمنع أجسام الطلبات الطبية والأسرار من التقرير. لا تُجمع counts متكررة من workflows مختلفة. يوقّع المخول كل بوابة وفق عقد القبول؛ تبقى غير المنفّذ/غير المتاح NOT_EXECUTED أو BLOCKED، لا PASS.
