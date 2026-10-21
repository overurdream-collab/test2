# قالب تقرير الاختبارات الخارجية

معرّف الوثيقة: `MCIAS-EXT-002` · الإصدار: 1.0 · الحالة: مسودة للمراجعة · اللغة: العربية

[English version](EXTERNAL_TEST_REPORT_TEMPLATE_EN.md) · [فهرس الحزمة](ACCEPTANCE_PACK_INDEX.md)

## تعريف التقرير

هذا **قالب فارغ**؛ كل النتائج الخارجية NOT_EXECUTED، ولا توجد توقيعات قبول. انسخ نسخة داخل المؤسسة، واربطها بـEXTERNAL_TEST_PLAN. اللغة الإنجليزية مقابلة بنفس المعرفات؛ عند التعارض يلزم حسم الجهة، لا افتراض ترجمة ملزمة قانونيًا.

| الحقل | القيمة عند البدء |
|---|---|
| رقم التقرير/المؤسسة/المضيف المعتمد | NOT_RECORDED |
| SHA كامل/بصمة الحزمة/مصدر الثقة | NOT_RECORDED |
| إصدار OS/Python/PostgreSQL/Node/Chromium والمكتبات والصور | NOT_RECORDED |
| الرأس Alembic الفعلي والمطلوب | NOT_RECORDED / 0019_reference_dataset_v1 |
| فترة الاختبار UTC/المشغّل/المراجع | NOT_RECORDED |
| نوع البيانات/مرجع الإذن/قواعد الاختبار | SYNTHETIC_PLANNED / NOT_RECORDED |
| RPO/RTO/Hجم العمل/التزامن/P95 المعتمد | NOT_APPROVED |

## النتائج

| ID | السيناريو/الأمر المنقح | النتيجة الفعلية | الدليل الداخلي وبصمته | العيب/إعادة الاختبار | المراجع |
|---|---|---|---|---|---|
| EXT-01 | حسب الخطة | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-02 | حسب الخطة | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-03 | حسب الخطة | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-04 | حسب الخطة | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-05 | حسب الخطة | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-06 | حسب الخطة | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-07 | حسب الخطة | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-08 | حسب الخطة | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-09 | حسب الخطة | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-10 | حسب الخطة | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |

PASS يعني تنفيذ الشرط وتحقيقه مع دليل؛ FAIL يعني تنفيذًا بنتيجة خاطئة؛ BLOCKED يعني تعذر شرط الدخول/ميزة غير متاحة؛ NOT_EXECUTED يعني لم يُنفّذ. لا تعادل SKIPPED نجاحًا، ولا يعتمد screenshot مالي وحده نتيجة مالية.

## ملخص العدّ والقياس

Python الناجح/الفاشل/المتجاوز: **NOT_MEASURED**. اختبار Seed المنفصل: **NOT_EXECUTED**. JS الناجح/الفاشل: **NOT_MEASURED**. مسارات المتصفح/أخطاء الصفحة/مخالفات WCAG: **NOT_MEASURED**. workflows/jobs وروابط CI وSHA لكل run: **NOT_RECORDED**. لا تجمع suite مكررة؛ اذكر كيف عولج كل skipped أو warning.

P50/P95/P99، throughput، CPU/RAM/IO، حجم البيانات، التزامن، الإحماء والمدة: **NOT_MEASURED**. مصدر الساعة وعدد العينات وأهداف SLA: **NOT_RECORDED**. زمن الاستعادة وفقد البيانات/BLOB hashes: **NOT_MEASURED**. مقارنة المصدر/المطالبات/الأدلة/اللقطات والتقارير: **NOT_EXECUTED**.

## سجل العيوب والاستثناءات

لكل عيب: ID، الخطورة، الدور/الشرط، خطوات إعادة إنتاج اصطناعية، المتوقع/الفعل، أثر مالي/خصوصية، الدليل المنقح، المالك، الإصلاح وSHA، نتيجة إعادة الاختبار، التبعات المتبقية والمراجع. استثناء مؤسسي مكتوب لا يلغي شرطًا إلزاميًا في عقد القبول؛ يجب حسم المتطلب أولًا.

## التوقيع والتسليم

قائد الاختبار/التاريخ: **NOT_SIGNED**. المراجع المالي المستقل/التاريخ: **NOT_SIGNED**. مسؤول الأمن/الخصوصية: **NOT_SIGNED**. المخول بقبول البوابة: **NOT_SIGNED**. البوابات المقبولة: **NONE_RECORDED**. القرار النهائي: **NOT_ISSUED**. العوائق المفتوحة: **NOT_REVIEWED**. مرجع أمر تفعيل الإنتاج، إن صدر لاحقًا: **NOT_ISSUED**.

الأدلة الطبية ومفاتيح الحسابات وملفات live-fixture لا تُرفق. تحفظ داخليًا بأذونات وبصمات؛ التقرير العام يذكر مرجعًا منقحًا فقط. لا تُرفع GATE_STATUS إلى ACCEPTED دون الأدلة والتوقيع لكل بوابة.
