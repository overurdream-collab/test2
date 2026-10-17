# دليل التسليم الفوري إلى Codex أو مبرمج بشري — MCIAS A1
**التاريخ المرجعي:** 2026-10-17. **الحالة:** نموذج تجريبي ببيانات اصطناعية، ليس معتمدًا إنتاجيًا.
**Repository:** https://github.com/overurdream-collab/test2
**Branch:** feat/mcias-a1-invoice-integrity
**Draft PR:** https://github.com/overurdream-collab/test2/pull/20
**Unmerged architecture draft:** https://github.com/overurdream-collab/test2/pull/19
**Original main baseline:** b69defa2f621458ef44d790b510840307a81009a
**آخر كود قبل تسجيل سياسة التوثيق:** 1ef2ede25ee123c5d9d353bca1c452837d730874؛ لا تفترض أن أي SHA لاحق مختبَر حتى ترى أدلة CI نفسها.

## الاستلام بالترتيب
1. اقرأ docs/engineering/TRACEABILITY_POLICY_AR.md ثم docs/engineering/worklogs/A1_2026-10-17.md؛ تحقق من آخر حدث وأحدث SHA على GitHub وأحدث نتائج CI.
2. اقرأ docs/agents/A1_INVOICE_INTEGRITY.md وdocs/agents/A1_EVIDENCE_REPORT_20261017.md وPR #19 بوصفه تصميمًا غير مدمج.
3. اقرأ mcias/agents/invoice_integrity.py؛ ثم ملفات النظام الموجودة: mcias/audit_agents.py وmcias/audit_engine.py وmcias/models_reference.py وmcias/models_claims.py وmcias/ingestion/reader_agent.py وmcias/palermo2.py.
4. اقرأ البيانات الاصطناعية والاختبارات tests/a1 وtests/test_a1_invoice_integrity.py؛ لا تُستخدم بيانات مرضى.
5. افحص Git diff وCI؛ سجّل النتيجة في حدث جديد، ثم غيّر الكود إذا لزم وسجّل كل تعديل واختبار في الـCommit نفسه.
6. لا تعدّل main ولا تدمج PR #20 ولا تنفذ A2 أو الربط الإنتاجي دون موافقة صريحة.

## الموجود سابقًا وما أضيف
الموجود في main: ReaderAgent/PDF/CSV/XLSX/OCR وPalermo-1؛ العقود والتعرفة G3 بتاريخ السريان؛ مطالبات G4 immutable؛ ثمانية فاحصين G5 وDecimal وPalermo-2؛ مراجعة بشرية G6 وتقارير G7/G8.
الجديد في A1: فصل الحسابات عن نموذج AI، مقارنة الوحدة والسعر والكميات الموثقة والرسوم المسموحة والإجماليات، عزل المؤسسات والعملات، امتناع INSUFFICIENT_EVIDENCE؛ لا كتابة بيانات المطالبات أو العقود ولا خصم مالي.
قيد معروف: سجلات G3/G4 الحالية لا تثبت دائمًا وحدة القياس الصحيحة للبند المفصل؛ ليس لدينا adapter إنتاجي مصرح به. يجب إثبات صلاحية attested وبصمة الملف الأصلي مستقلًا قبل الاستخدام الحقيقي.

## إعادة الاختبار
~~~bash
git clone https://github.com/overurdream-collab/test2.git
cd test2
git fetch origin
git checkout feat/mcias-a1-invoice-integrity
git rev-parse HEAD
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest tests/test_a1_invoice_integrity.py -q
python -m scripts.evaluate_a1 --output a1-results.json
python -m scripts.compare_a1_g5_baseline --output a1-g5-comparison.json
python -m unittest tests.test_traceability -v
python scripts/check_traceability.py
~~~
للاختبارات الكاملة استخدم قاعدة PostgreSQL اختبارية منفصلة فقط (راجع docs/INTEGRATED_CANDIDATE_HANDOFF_AR.md)؛ لا تنفذ أي ترحيلات/Reset على قواعد حقيقية. لا تساوِ نجاح اختبارات unit بمرور اختبارات PostgreSQL.

**النموذج الحقيقي (اختيارياً عند توفر 10 GiB RAM تقريبًا أو أكثر):**
~~~bash
python -m pip install "llama-cpp-python>=0.3.9,<1" "huggingface_hub>=0.30,<2"
python -m scripts.a1_probe_local_model --download-public-model --repo Qwen/Qwen3-8B-GGUF --output a1-real-model-evidence.json
~~~
تنزّل الأوزان العامة فقط، ويُستدل محليًا ولا تُرسل مطالبة حقيقية لأي خدمة. Model: Qwen3-8B GGUF Q4_K_M، revision 7c41481f57cb95916b40956ab2f0b139b296d974، SHA256 d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785.

## آخر نتائج مثبتة قبل هذه السياسة
43 targeted tests PASS (https://github.com/overurdream-collab/test2/actions/runs/39053124523). قواعد A1 على 18 حالة: TP7 FP0 FN0 TN2 مع 9 حالات امتناع؛ 8B على 36 حالة اصطناعية بعد إصلاح مصدر الأدلة: TP10 FP0 FN0 TN26، متوسط 8.775 ثانية وذروة RSS 10,148,124 KiB (https://github.com/overurdream-collab/test2/actions/runs/39051968767). الفشل السابق: 26 حالة TP8 FP2 FN0 TN16، 80% Precision (https://github.com/overurdream-collab/test2/actions/runs/39051176994). لا تعتبر إعادة اختبار المجموعة نفسها تقييمًا أعمى جديدًا.
مقارنة G5 ذات ست حالات فقط: A1 TP3 FN0، محرك G5 باستخدام مؤشر خصم غير صفري TP2 FN1؛ لا تُعمم على المطالبات الحقيقية.

## المسائل المفتوحة
مجموعة blind gold مع مختصي الفواتير، مصدر مؤسسي معتمد للوحدات والكميات وصلاحية الاستشهاد، Palermo للتحقق من بصمات الملف والاقتباسات، اختبار أصناف/عملات/مستندات متنوعة، ثم مراجعة بشرية وتفويض مؤسسي. Professor OS/AI Gateway وPalermo وG6/G7 تكاملات مستقبلية وليست مُفعلة هنا. لا تعلن جاهزية إنتاجية ولا تقل كشف الاحتيال مؤكّد.

## نص جاهز لتسليم المهمة
أنت مهندس MCIAS A1: اقرأ أولاً سياسة التتبع والسجل التاريخي ودليل التسليم ووثائق الوكيل وPR #20 وPR #19. تحقق من SHA وCI وقائمة الاختبارات كما هي، ولا تفترض نجاح اختبار لم تنفذه. استكمل فقط الأعمال المفتوحة والمسموحة لـA1 باستخدام بيانات اصطناعية ونموذج مفتوح الأوزان محليًا دون API مدفوع. سجّل كل قراءة وقرار وكتابة واختبار وفشل فورًا؛ أي Commit تعديل يتضمن سجل العمل بنفسه. لا تعدّل main ولا تدمج ولا تبدأ A2.


## P0 تنفيذ تكليف المراجعة المستقلة (2026-10-17)
اقرأ تقرير البحث `docs/agents/A1_OPEN_SOURCE_RESEARCH_AR.md` أولًا؛ تم فحص PR #22 وPR #23 وتأكد أنهما Draft، وContract Intelligence لا يملك تفويض تفعيل مالي. لا تجلب أسعارًا من Draft. باقي الأعمال: trusted source adapter مستقل، Palermo SHA تحقق أصل المستند، Pydantic contract، اختبارات تاريخ H1/H2 وCI على SHA التنفيذ. أي بيانات ناقصة ترجع INSUFFICIENT_EVIDENCE لا أسعارًا مخترعة.
