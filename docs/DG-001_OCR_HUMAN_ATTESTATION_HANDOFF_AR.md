# DG-001 — OCR Human Attestation — ISOLATED IMPLEMENTATION & HANDOFF

**الحالة:** تجريبي بالكامل — منع الدمج والنشر والتكامل التشغيلي. بيانات ومؤسسات وحسابات مراجعين اصطناعية فقط.

## التسليم والبنية المُعاد استخدامها

- يستكمل **Document Reader** نفسه على الفرع `feat/mcias-document-reader-isolated-pilot`، ولا ينشئ وكيلًا مستقلًا أو يغيّر G2 التشغيلي.
- `scripts/document_reader_human_review_pilot.py`: خادم FastAPI عبر `127.0.0.1` فقط؛ يعيد استخدام `mcias.storage.EncryptedStore` و`mcias.ingestion.orchestrator.ingest` و`IngestionDocument` و`IngestionJob` و`Candidate` من تجربة OCR السابقة، بالإضافة إلى `reopen` للتحقق من الأصل. SQLite اصطناعية معزولة ومفتاح AES-256-GCM مؤقت.
- `scripts/document_reader_human_review.html`: واجهة فعلية لتسجيل الدخول الاصطناعي، اختيار PDF، انتقال الصفحات، عرض PNG الناتج عن إعادة فتح الأصل المشفر، طبقة مواضع الأدلة، معاينة مكبرة للخلية، النص المقروء، نسبة OCR غير المعايرة، وتسجيل قرار المراجع.
- `scripts/test_document_reader_human_review.py`: تشغيل خادم loopback فعلي مع جلسات HTTP ومستعرض Chromium Playwright. النقرات والإجراءات الاختبارية تُنشئ **مراجعة محاكية**، وليست تأكيد مراجعة بشرية مستقلة.
- `.github/workflows/document-reader-human-review-isolated.yml`: Workflow معزول يثبت A1 على SHA `b536a94adf4d190ac48856bd435a8a624f3931f4`، ويشغل المتصفح والاختبارات ويرفع الأدلة بما فيها صورة الشاشة.

## عقد الحالات وصلاحياتها

`UNVERIFIED_OCR_CANDIDATE` → `PENDING_HUMAN_REVIEW` أو `TRANSCRIPTION_ACCEPTED` أو `TRANSCRIPTION_CORRECTED` أو `REJECTED` أو `UNRESOLVED`.

قبول النقل **لا** يعني إثبات حصول الخدمة الطبية ولا موافقة تعاقدية أو مالية. التصحيح يتطلب سببًا وقيمة، والرفض وعدم الحسم يتطلبان سببًا. تعديل قبول سابق لا يبدّل الحدث، بل ينشئ إصدارًا جديدًا مع السبب. هوية المراجع والمؤسسة مستمدتان من تسجيل دخول الخادم المؤقت، ولا يمكن تمريرهما في عقد قرار الطلب.

جدول `reader_ocr_candidate_isolated` الأصلي يبقى بصفوفه وحالته غير الموثوقة. `reader_isolated_evidence_seal` يحفظ بصمة صورة السجل النصية المؤرخة؛ `reader_isolated_review_events` يسجل معرّف المؤسسة والمستند والمرشح وSHA-256، والصفحة والإحداثيات وقيمة OCR الأصلية، والحالة القديمة والجديدة، والقيمة المصححة، وهوية مراجع الخادم والوقت والسبب والإصدار وOperation ID وهاش الحدث السابق وهاش الحدث الحالي. SQLite triggers تمنع UPDATE وDELETE لهذه الجداول في بيئة التجربة، مع تحقق من سلسلة الهاش عند القراءة. هذا **ليس** بديلًا تشغيليًا لـShared Audit أو سجلًا محميًا من امتيازات مدير قاعدة البيانات؛ يجب استخدام خدمات التدقيق المشتركة عند تكامل مستقل معتمد.

يتطلب القرار إصدارًا متوقعًا وOperation ID: إعادة الطلب نفسه عملية Idempotent تعيد الحدث السابق، أما تعارض الإصدارات أو إعادة استخدام العملية بمعطيات مختلفة فيُرفض. لا يُقبل `TRUSTED` أو أي اعتماد مالي ضمن عقد الحالات.

## سلسلة التحقق المستقلة

1. استرجاع المستند من `EncryptedStore` عبر `IngestionDocument` المقيد بمؤسسة المراجع والتحقق من SHA-256.
2. رسم صفحات PDF الأصلية وإظهار مربعات الأدلة فوق الصفحة نفسها؛ لا إرسال إلى خدمات OCR خارجية.
3. الاحتفاظ بالحقول الأولية دون تعديل مباشر، وتسجيل تصحيح النقل بشكل مستقل في `ReviewEvent`.
4. إعادة قراءة الأصل المشفر وإعادة إجراء OCR مستقل عن سجل القرارات عند التأهيل، ثم مقارنة معرّف البند والقيمة الأصلية والنص والصندوق الإحداثي، والتحقق من سلامة سلسلة المراجعات. تصحيح المراجع لا يصبح مؤكد الدلالة طبيًا: هو تصريح بشري بشأن النقل فقط.
5. محول تجريبي يستدعي `analyze` الأصلية في A1 على البنود المكتملة المراجَعة، ولا يستدعي `a1_trusted_input` أو يضبط `extracted_rows_equal_original=True`. كل نتائج المعاينة `HUMAN_REVIEW` و`financial_decision=NOT_AUTHORIZED`.

## سيناريوهات القبول والرفض

A: الفاتورة الإنجليزية الصحيحة، مراجعة نقل الحقول كاملة، ثم A1 استشاري دون تناقض حسابي.

B: فاتورة بإجماليات متبادلة: يقبل المراجع **نقل ما هو مطبوع** دون تصحيح آلي للمبلغ؛ تكشف A1 تناقضين حسابيين.

C: فاتورة عربية بتاريخ غير محسوم: تمنع المعاينة المالية عند نقص المعلومة ولا يُخمن التاريخ. نقصان أو عدم اعتماد حقل السعر يبقي المعاينة معلقة كذلك.

اختبارات الرفض تشمل تعديل سجل أصلي دون إصدار، تغيير معرّف المؤسسة، محاولة حقن الهوية أو المصدر في القرار، إعادة Operation ID بمحتوى مختلف، التكرار الصحيح Idempotent، تنازع إصدارين، تعديل SQLite للسجلات Append-only، رفض/عدم حسم دون سبب، مطالبة TRUSTED أو صرف مالي، تغيير أصل مخزن AES-GCM، وصفحة PDF غير موجودة.

## حدود الاعتماد

الواجهة تعرض حقولًا **بإحداثيات OCR أصلية** وليس إحداثيات ثابتة من قالب التصنيع، لكنها ما زالت تعمل على ثلاث فواتير اصطناعية من القوالب السابقة ولا تثبت جودة OCR في فواتير واقعية. إعادة OCR تستخدم المحرك نفسه وليست شاهدًا بصريًا مستقلًا؛ يبقى قرار التصحيح البشري عملية مُحاكية في CI. بيانات السر التجريبي ليست صلاحيات إنتاج ولا يمكن إطلاق الخادم خارج loopback؛ لا تنطبق ضوابط دخول المؤسسة وتشغيل Shared Audit هنا على بيئة حقيقية.

مستندات G2 ما زالت `review_required` ولم تُنشأ `ExtractedSourceRecord` موثوقة أو تغييرات Alembic. عقد A1 الحالي لا يقبل PDF/OCR المراجَع بصفته G2 trusted input. **NO MERGE / NO DEPLOY / SYNTHETIC DATA ONLY.**

## Worklog / Final Evidence

- نقطة الاستئناف الموثقة: `0a60656bcb61912193772d8d842952bc0885f00a` مع اعتماد 54/54 أدلة OCR و7/7 حالات رفض وعدم إعادة تجارب G2 القديمة.
- تنفيذ الخادم والواجهة وسجل Append-only والاختبار الحي والبوابة على الفرع نفسه.
- **لا تدّعِ نجاح CI قبل فحص أحدث SHA وروابط تشغيل GitHub Actions**. النتائج الفعلية وتفاصيل العيوب إن وجدت تُذكر في التقرير النهائي.


## تشغيل الواجهة محليًا — ضمن بيئة صناعية معزولة فقط

تُجهز CI اعتماديات `python -m pip install -e '.[test,browser]'` ومحرك `Tesseract` المحلي، وتُثبت الملف الأصلي `mcias/agents/invoice_integrity.py` من PR #20 عند SHA المشار إليه أعلاه. لتشغيل واجهة التجربة من جذر الفرع دون نشرها:

```bash
PYTHONPATH=.:scripts python scripts/document_reader_human_review_pilot.py \
  --a1 pinned-a1-readonly/mcias/agents/invoice_integrity.py \
  --workdir /tmp/mcias-reader-review-demo --port 8765
```

العنوان التجريبي: `http://127.0.0.1:8765/`. حسابا المراجعة الاصطناعيان:
`reviewer-a` / `demo-reviewer-a-2026` و`reviewer-b` / `demo-reviewer-b-2026`.
هذه البيانات منشورة قصدًا **للتجربة المحلية فقط**، ولا تتضمن صلاحيات نظامية أو كلمات مرور حقيقية. كل تشغيل ينبغي أن يستخدم مجلدًا جديدًا، لأن مفتاح المخزن المؤقت يتغير عند إعادة التشغيل.

## دليل تنفيذ مرجعي تمت مراجعته

- [Run #39403452038](https://github.com/overurdream-collab/test2/actions/runs/39403452038): **SUCCESS** على SHA `152892f3f5fd83af93ac1a324400eae9d78a1df4`.
- تشغيل Chromium حقيقي أظهر صورة PDF و18 مربع دليل، واختبر الانتقال بين صفحتين، ورفع لقطة الشاشة إلى Artifact `reader-human-review-browser-and-api-synthetic`.
- السجلات أثبتت **40 قرار مراجعة اصطناعيًا**، واختبارات رفض تعديل أحداث SQLite والتعديل المباشر لسجلات OCR، وتكرار الطلب Idempotency، والعزل بين المؤسسات، وانتحال هوية، ورفض الأصل المشفر المعدل. A1 اكتشف تناقضين في الفاتورة ذات المبالغ المتبادلة.
- الاختبارات تُحاكي النقرات وقرارات المراجع، ولا يوجد أي إثبات بأن مراجعًا بشريًا مستقلًا قام بهذه المهمة.
- تستكمل التجربة الإضافية على أحدث SHA قيد التحقق اختبار التصحيح مع **نوع الحقل الصحيح**، ورفض كتابة النص في حقل السعر، وعودة A1 بتناقض حسابي بعد تعديل سعر بشرط إصدار مراجعة جديد، مع بقاء قرار المطالبة `HUMAN_REVIEW`.

**قرار الاعتماد مرهون بنجاح آخر CI على SHA المحدث، ولا يتعدى نطاق Human Review المعزول.**

## Final independent QA evidence — 2026-10-20

- Updated strict-field correction checks **passed** on `9e5a2f3fb51ae6dfb740ee1f3ae7d30ec72eb617`; the final documentation-head verification on the same code **passed** in [Run #39403907977](https://github.com/overurdream-collab/test2/actions/runs/39403907977) at `fbd084e739b8500b39bec971e5a04e4bee41b573`.
- Report: 3 synthetic documents; 18 visual source anchors in Chromium; 2-page navigation demonstrated; **41 synthetic decisions** including versioned correction, A1 arithmetic 0 / 2 before correction and 1 after a deliberate synthetic price amendment, pending/reject/unresolved; hash/event immutability and cross-tenant/identity controls tested.
- Artifact: `reader-human-review-browser-and-api-synthetic` in Run #39403907977, containing `human_review_results.json`, `server.log` and `review_ui_after_accept.png`. QA inspected the screenshot: original PDF raster, source-cell overlays, zoom crop, accepted state and page controls rendered correctly.
- All attestation actions were scripted by tests, **not performed by a real independent reviewer**; this is not a qualification of human visual correctness.
- Source rows remain `UNVERIFIED_OCR_CANDIDATE` and the G2 documents remain `review_required`. There is no new production table, migration, Shared Audit service, live data, deployed interface or financial outcome. A1 `a1_trusted_input` remains unmodified and unused.
- **Decision: ISOLATED HUMAN REVIEW PILOT ACCEPTED** for functional synthetic HTTP/Chromium review, append-only demonstration and advisory A1 preview only. Formal OCR review permissions, Shared Audit integration, resilient centralized event retention and trusted PDF row authorization remain future separately approved work. **NO MERGE / NO DEPLOY.**

