# سجل تنفيذ MCIAS — ملحق مالك Document Reader

هذه النسخة المعزولة لم تتضمن سجل المنسق العام؛ هذا إدخال مالك محدود لإلحاقه بالسجل العام عند التنسيق، وليس إعادة كتابة لسجلات المسارات الأخرى.

### HANDOFF-20261021-303 — E2 frozen-source geometry comparison
- Scope: استئناف الفرع القائم codex/document-evidence من d62e2bfa44ad662fb7a3628b0622a98f7f01787f، وتحسين موضع القيم في المقياس القائم على8صور اصطناعية و30حقلاً دون لمس نواة G2/G3/G4/G5/A1.
- Why: إثبات موضع القيمة منفصلًا عن صحة قراءتها، ومعالجة فشل TSV البيئي الصامت دون احتساب صفر الحقول كخط أساس دقة.
- Files: scripts/document_reader_dg002b_benchmark.py، tests/test_document_reader_e2_regions.py، .github/workflows/document-reader-dg002b-benchmark.yml، docs/E2_READER_COMPARISON_AR.md، docs/evidence/e2_reader/*، وهذا السجل وملحق الحالة.
- Tests: فعليًا23 PASS؛ Tesseract5.5.0 محلي CPU مع eng/ara ذات بصمات محفوظة؛ مقارنة8صور مجمدة30حقلاً؛ git diff --check PASS. CI على Commit الجديد PENDING، دون رابط نجاح مختلق.
- Result: ISOLATED VERIFIED للموضع26→30/30 والقيمة+الموضع22→23/30؛ النص ثابت23/30 والعربية8/15 QUALITY BLOCKED. جميع30 للمراجعة، صفر قرار مالي. قص العربية التجريبي لم يرفع الدقة ولم يُعتمد.
- Risks: نماذج بسيطة بتسميات معروفة، ثقة غير معايرة، لا شهادة أصل G2 أو تكامل G5 أو جودة طبية/مالية عامة. زمن17.017→17.019 ثانية للموضع، والقص25.039 ثانية؛ ذاكرة فردية42.770MiB وليست إجمالي RSS.
- Next: المشرف ينشر Commit المالك دون force/merge ويشغل CI المطابق، ثم مراجعة مستقلة للدليل؛ تحسين العربية يحتاج اختبارًا مستقلاً معلن المصدر دون تخمين/تدريب/أوزان ثقيلة.
- Handoff: docs/E2_READER_COMPARISON_AR.md وdocs/evidence/e2_reader. إعادة التنفيذ موثقة؛ لا بيانات حقيقية أو merge أو deployment أو قرارات مالية/سريرية.

### HANDOFF-20261021-305 — اعتماد إصلاح الأمن دون دمج
- Scope: نقل ملفات مالك الاعتمادات الستة المعتمدة من PR33/6454b6d054591e398c7251af5454c067fa00fc59 إلى فرع Reader القائم بعد cf886f4517b2502acbaf96b1703911ca14986440.
- Why: منع إعادة إدخال Pillow12.3.0 وثغراته عند نشر فرع Reader.
- Files: pyproject.toml، scripts/audit_dependencies.py، tests/test_dependency_audit.py، tests/test_pillow13_compatibility.py، .github/workflows/ci.yml، .github/workflows/workspace.yml؛ وتقرير E2 وسجلا DG001 ودليل التوافق.
- Tests: الملفات الستة مطابقة بايتياً للمصدر6454b6d. دليل الأمن المعاد استخدامه: 65 حزمة خارجية بلا ثغرات و34 توافق؛ أعيدت اختبارات التوافق على Reader فعليًا: 34 PASS في15.50 ثانية دون تخطٍ. لم يُعد Dependency Audit أو OCR Benchmark؛ git diff --check PASS.
- Result: IMPLEMENTED/ISOLATED VERIFIED ضمن إصلاح الاعتمادات وتوافق الصور/OCR/PDF؛ Pillow>=13.0.0,<14 وتدقيق خارجي صارم دون تجاهل الثغرات. CI على Commit Reader الجديد PENDING.
- Risks: نتيجة65 تخص تشغيل الأمن السابق لا فحص Reader جديد؛ جودة العربية وتكامل G2/G5 كما في HANDOFF303 لم تتغير.
- Next: المشرف ينشر على فرع Reader الرسمي القائم ويجهز Draft PR ثم يتحقق من CI على SHA المطابق؛ لا merge.
- Handoff: docs/E2_READER_COMPARISON_AR.md وسجل security_compatibility_pytest.txt وبيان security_adoption.json؛ لا imports E1 أو تغيير Gold أو فرع جديد أو merge/deployment/force push.

### HANDOFF-20261021-306 — إصلاح تثبيت تبعيات مشغّل Reader
- Scope: متابعة PR35 على فرع Reader القائم؛ HEAD المنشور869f79f وشجرة HEAD المحلي e89b6bd متطابقان وفق تحقق المشرف، والشجرة المحلية نظيفة قبل الإصلاح.
- Why: التشغيل الفعلي39590938187 فشل قبل جمع الاختبارات لأن conftest يستورد sqlalchemy غير المثبتة في قائمة OCR الجزئية؛ فشل إعداد بيئة لا دقة OCR.
- Files: .github/workflows/document-reader-dg002b-benchmark.yml، docs/E2_READER_COMPARISON_AR.md، وهذا السجل وملحق الحالة فقط؛ صحح التقرير أيضًا مرجع إدخال الأمن إلى305 المتفق عليه.
- Tests: لم تُعد الاختبارات أو Dependency Audit أو OCR Benchmark الناجحة. تحقق المشرف من نجاح G1–G7 متضمنًا التدقيق على HEAD المنشور نفسه؛ فُحص diff وgit diff --check محليًا.
- Result: IMPLEMENTED / REVIEW PENDING؛ تثبيت الحزمة المحلية -e '.[test]' يستبدل القائمة الجزئية في workflow Reader مع بقاء Pillow13 وTesseract. لم يتغير اختبار أو conftest أو Gold.
- Risks: نجاح Reader على SHA الإصلاح الجديد غير مثبت بعد؛ القياسات السابقة وحدود جودة العربية كما في303 دون تغيير.
- Next: المشرف يراجع Commit وينشره على فرع Reader الرسمي القائم، ثم يتحقق من التشغيل المطابق ويحتفظ بأي فشل؛ لا merge أو deployment.
- Handoff: https://github.com/overurdream-collab/test2/actions/runs/39590938187 وdocs/E2_READER_COMPARISON_AR.md؛ فشل المشغّل الأول محفوظ، واختبارات التوافق34 والقياس23 السابقان لا يعادان محليًا.

### HANDOFF-20261021-404 — E4 metadata source roles and conservative A1 gate
- Scope: فرع Reader القائم من66ab51f، تحليل7أخطاء عربية محفوظة وإصلاح ربط metadata فقط، مع holdout جديد صغير وتوافق workflows/pilots المتأثرة.
- Why: RED مثبت: أول effective date اختير service_date، ومقدم غير SYNCLINIC لم يقرأ؛ صحة الموضع لا تصحح أخطاء OCR العربية ولا تمنح سلطة مالية.
- Files: scripts/document_reader_dynamic_layout_pilot.py، scripts/document_reader_e4_quality.py، tests/test_document_reader_e4_metadata.py، caller qualification وcaller reviewed-PG للـReader، workflow structured وshared-audit-reader، docs/E4_READER_QUALITY_AR.md، docs/evidence/e4_reader/* وسجلا DG001.
- Tests: RED2FAILED/6DESELECTED/2.14s؛ GREEN10PASS/0.82s؛ holdout3PDF فعلية: metadata16/16 نص وربط، الجدول23/24 نص و24/24 موضع للحالتين غير المتعارضتين؛ تعارض التاريخ وعبث المصدر محجوبان. diff/compile PASS؛ لا إعادة23اختبارًا أو8صور أوAudit أوPG.
- Result: ISOLATED VERIFIED لربط الحقول المحدد، QUALITY BLOCKED للعربية والأهلية المالية. جميع A1 payloads محجوبة بسبب ثقة rowid، والثالث أيضًا بسبب تعارض service_date. DATE العام لا يعود تاريخ خدمة؛ قيم Gold القديمة لم تتغير. Pillow13 في القيود الثلاثة للـworkflow المتأثر.
- Risks: عينة صغيرة بتسميات مضبوطة ومعظم metadata إنجليزي؛ CER0.011968/WER0.024390 لا يقارنان بالمجموعة القديمة؛ العربية السابقة8/15 لم تتحسن. لا شهادة G2 أو تعرفة معتمدة أو قرار مالي.
- Next: المشرف ينشر Commit على PR35 القائم ويشغل CI المطابق؛ مراجعة مستقلة لأهلية الاستهلاك قبل أي تكامل موثوق، دون توسيع تجارب هذه الوحدة.
- Handoff: docs/E4_READER_QUALITY_AR.md وdocs/evidence/e4_reader؛ جميع المرشحات UNATTESTED_OCR_CANDIDATE وHUMAN_REVIEW، وبقيت أعلام G2/A1 المالية false؛ لا merge/deploy/force push/real data.
