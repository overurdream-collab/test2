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
