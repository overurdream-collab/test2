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


## P0 Trusted A1 Input Adapter (CSV-only)
اقرأ docs/agents/A1_DATA_CONTRACT_AR.md وmcias/agents/a1_trusted_input.py. يعيد قراءة الأصل المشفر ويطابق الصفوف؛ لا يحوّل G3 amount إلى unit price دون توثيق. لا API حقيقي بعد ولا PDF OCR ولا attested proof. جميع الاختبارات على هذا التغيير PENDING_CI قبل ظهور سجل CI.

مرجع XLSX الجديد: يستعمل G2 file_scanner وisolated_parse في عملية محدودة ومقارنة البايتات ثم الصفوف؛ راجع tests/test_a1_trusted_input.py؛ PDF/OCR ما زال غير مؤهل للمقارنة المالية. لا مصدر لتوثيق تنفيذ الخدمة أو وحدة التعرفة.

تطوير فحص Duplicate (فقط داخل A1): إذا استُخدم موضع الصف الأصلي نفسه مع نفس الكميات/القيم في بندين مختلفين، يصدر POTENTIAL_INTERNAL_DUPLICATE للمراجعة بلا توفير مالي مرشح؛ تكرار service_code على صفين مستقلين لا يعد تكرارًا.

أمان HTTP: App security middleware يفرض Cache-Control: no-store على جميع المسارات /api/v1/a1/، واختبار مثبت ضمن tests/test_a1_preview_http.py. CI الخاص بـA1 يشمل اختبارات G2/G4 adapter وHTTP إلى جانب القواعد والنموذج الحقيقي.

Guard بعد hash: لا تقبل G4 ClaimEntry إن لم تطابق قيمها المطَبّعة بيانات صف G2 الأصلية حرفيًا/عددياً؛ تراجع الاختبارات tests/test_a1_trusted_input.py::test_g4_normalized_claim_amount_cannot_diverge_from_original_source. صلاحيات source medical_fields تغطي G4 fields والـinvoice.

## A1 → G6/G7 وPR22 الأربع نتائج (واجهة قراءة فقط)
أضيف mcias/agents/a1_review_packet.py؛ تنتج preview_a1_from_g4 حزمة review_packet مع أصل كل finding ونسخة المصدر، وHUMAN_REVIEW أو MISSING_ATTACHMENTS **مبدئيًا فقط**. لا يمكن للوكلاء إصدار ACCEPTED_RULES أو REJECTED_RULE_CERTAIN ولا اعتماد خصم؛ Palermo='NOT_EXECUTED'، G6='PENDING' وG7.realized_savings=null. هذا اتفاقية بيانات بين الوكلاء وليس نشرًا أو تكاملًا على قواعد G6/G7.

## 2026-10-17 P0 مستقلة قابلة للاستلام
جدول كل ملاحظة للمراجع وحالتها ومصدرها: docs/agents/A1_REVIEW_GATE_MATRIX_AR.md. آخر كود P0 مختبر على 0962b54a (G1–G7 وG9 وتتبّع PASS). docs/engineering/STATE_A1.json حالة مقروءة آليًا، ليست بديلاً من GitHub HEAD. PR #22 DG-001 وPR #23 غير مدمجين؛ packet تمهيدي لا قرار G6 نهائي. اختبار بيانات صناعية لا يمنح اعتماداً إنتاجيًا.


## استئناف آمن بعد التوقف — فحص GitHub على f4729b109f5e22a85ebb7a55192858b530a9e60d

**آخر عملية مكتملة:** تحديث مصفوفة DG-001 وحالة التسليم في Commit `f4729b109f5e22a85ebb7a55192858b530a9e60d`. آخر تعديل كود A1 كان في `0962b54a896c572fc8db9d74d6d33cb044d25601`. لا تعد إنشاء G2/G4 adapter أو PDF/XLSX parser ولا API ولا review_packet؛ الملفات والاختبارات موجودة.

تحقق على **SHA f472** من جميع الأنواع: A1 57 pytest PASS؛ Qwen3-8B 36 استدلالًا حقيقيًا TP10 FP0 FN0 TN26؛ G1–G7 405 PASS و19 SKIP، PostgreSQL والتبعيات PASS؛ Enterprise/Browser 423 PASS و1 SKIP؛ G9 PASS؛ CI traceability صفر مخالفات. الروابط الدقيقة في `docs/agents/A1_REVIEW_GATE_MATRIX_AR.md` و`docs/engineering/STATE_A1.json`. لا تُدّعِ أن نجاحها يثبت دقة طبية خارج مجموعة بيانات اصطناعية سبق فحصها.

**ما لا يجوز إغلاقه الآن:** مرجع السعر حسب وحدة معتمد وموقع G3/G5، إثبات طبي مستقل لواقعة تنفيذ الخدمة في Palermo، corpus blind عربي/إنجليزي PDF/OCR بمرجع مختصين، قرار مؤسسة دمج PR #22/#23، وتكامل G6/G7 الإنتاجي. لا يوجد تفويض يحوّل مبلغ G3 المجمل إلى سعر وحدة أو يسمح بخصومات تلقائية. تابع بإعداد مواصفات قبول Palermo وعينات blind مصرح بها، دون جلب بيانات حقيقية غير مصرح بها أو إرسالها إلى سحابة.

**تحديث الحالة بعد هذا التسليم:** اقرأ دائمًا HEAD الجديد ومخرجات CI من GitHub قبل ادعاء نتيجة جديدة؛ الملف يوثق اختبارات SHA السابق تحديدًا، والـCommit الوثائقي الجديد يخضع لفحص CI منفصل. لا تغيّر `main` ولا PR22/23 ولا تُكرر التعديلات.


## استئناف المرحلة الأولى — إضافة item_kind اختياري من مصدر G2
أضيف احتفاظ المحوّل بنوع بند الفاتورة `item_kind` عندما يكون `service` أو `fee` صريحًا في CSV/XLSX الموثق (بدون تخمين). القيم غير المعروفة تبقى ناقصة الدليل. يبقى نظام التسوية مغلقًا، ولا تتغير بوابة G3/G5 المالية. راجع اختباري النوع والرفض في `tests/test_a1_trusted_input.py` ونتائج CI على Commit هذه الدورة قبل متابعة أي تغيير. **التالي:** تقييم مقاييس الحقول الأصلية لأنواع الخدمات والرسوم ومعايير تحديد بنود fee المصرح بها بعد صدور دليل عقدي مؤسسي؛ لا تفعّلها افتراضيًا.


## شرط استئناف المرحلة 1 — رسم بلا مصدر بند تعاقدي
نفذ حاجز `FEE_CONTRACT_AUTHORITY` داخل A1: `allowed_fees` ليس تفويضًا مستقلًا، ويشترط مصدر بند رسوم مطابقًا لهوية وصمة مصدر العقد الساري. مصدر مفقود/مخالف => `INSUFFICIENT_EVIDENCE`، ولا يعتبر الرسم مباحًا أو مرفوضًا قطعًا. توجد ثلاثة اختبارات داخل tests/test_a1_invoice_integrity.py. **التالي:** التحقق من نتيجة GitHub Actions على آخر SHA؛ ثم مراحل لاحقة فقط بعد اعتماد مصدر G3/G5 رسمي، وعدم بدء Palermo في هذه الجلسة.


## دورة المرحلة 1: إشارة missing_evidence متخصصة للرسوم
بعد التحقق من بيانات G2/G4، أصبح ظهور `item_kind=fee` يؤدي إلى حقل `approved_contract_fee_clause` ضمن الأدلة الناقصة. لم تُضاف أسعار G3 أو صلاحيات مالية، وبقي `contracts=[]`. تأكد من CI على SHA الدورة، وراجع سجل الحدث أدناه. أول عمل لاحق: إقرار شكل وتوقيع وحفظ جدول رسوم عقدي من الجهة المخولة، قبل ربطه فعليًا، ولا تستنتج الرسم من تعرفة الخدمة.


## توقف المرحلة 1 — ربط رسوم G3 / ReferencePoint مشروط لا يُخمن
تم فحص `mcias/models_reference.py` وملفات `mcias/models_reference_points.py` و`mcias/reference_points.py` من Draft PR #22 عند SHA `b694a2a1603a9a4c6d7af26ed56035b1a28b0166`؛ **لا يوجد حتى الآن حقل معتمد يربط بند `fee` بسعر وحدة ورسوم العقد، هوية العقد، وحالة اعتماد مؤسسي موقّع مع مصدر إلزامي**. لا تغيّر A1 production أو تضف استنتاج رسوم من `ProviderTariff` أو `ReferencePoint.section=tariffs`. أُضيف اختبار صريح يجبر هذا الامتناع ويثبت حالات ثلاث بمرجع عقدي اصطناعي. استأنف أولًا من التحقق من CI على SHA الجديد، ثم من مواصفة/اعتماد تخزين هذه المرجعيات في فرع تكامل مستقل، بعد مراجعة PR22 وموافقة مالك السياسة؛ لا تنتقل للمرحلة الثانية.


## مرحلة 1 — الفصل الآلي بين تعرفة الخدمة ورسوم الفاتورة
بعد تطبيق `approved_contract_fee_clause`، يصدر تشخيص G3 الآن `additional_fee_authority=NOT_ESTABLISHED` عند وجود بند `fee`، حتى إن كانت تعرفة خدمة G3 تاريخية صالحة. اختبارات `test_approved_g3_service_tariff_cannot_authorize_itemized_fee` و`test_legacy_service_only_invoice_does_not_invent_missing_fee_clause` تغطي جانبي التفريق. لا تفعل رسوم معتمدة تلقائيًا أو تدّع ربط PR22؛ تحقق من CI على SHA الجديد أولًا.


## استلام دورة مرجع الرسوم — رفض التفعيل لغياب الصلاحية
آخر فحص: G3 `ProviderTariff` تعرفة خدمة، ولا توجد جهة رسوم مصدقة؛ PR22 ReferencePoint مصدره اختياري ولا FK لإصدار العقد/نوع رسم/وحدة/توقيع بند؛ PR23 Contract Intelligence مصدره `DRAFT_ONLY` ولا يروّج إلى اعتماد مالي. أبقِ `approved_contract_fee_clause` و`additional_fee_authority=NOT_ESTABLISHED`، ولا تفتح `allowed_fees` لمدخلات غير مصدقة. اختبار expiration الاصطناعي الجديد في `tests/test_a1_invoice_integrity.py`. تحقق من CI عند آخر SHA ثم توقف ضمن المرحلة الأولى لحين مواصفة واعتماد المؤسسة. لا دمج أو بدء Palermo.


## مرحلة 1 — مقترح مخطط رسوم بلا تفعيل (2026-10-18)
على SHA التالي للمؤشر `bcccfe00538d47edd5b8816e3ff680a6f5667d13`، أضيف `mcias/agents/a1_fee_reference_contract.py` و`tests/test_a1_fee_reference_contract.py` كـPydantic schema غير متصل بقاعدة البيانات. التوقيع مجرد ميتاداتا NOT_VERIFIED وكل مدخل NOT_AUTHORIZED. راجع `docs/agents/A1_FEE_REFERENCE_PROPOSAL_AR.md` وسجل الحدث. التالية: فحص CI exact SHA، ثم إقرار تخزين ومطابقة وتوقيع مؤسسي قبل أي ربط فعلي؛ لا تعيد بناء G3/PR22/23 ولا تفترض موافقة الرسوم.


## نقطة استئناف مطابقة مرجع الرسم
أضيفت مقارنة قراءة فقط في `mcias/agents/a1_fee_reference_contract.py` مع اختبارات اصطناعية للهوية والمصدر والتواريخ والحالة. النتيجة البنيوية لا تخول ماليا، حتى عند تطابق القيم. راجع CI للـSHA الجديد، ثم اطلب دليل توقيع مؤسسي مرتبط بالمستند والعقد قبل أي تكامل فعال.


## فحص توقيع الرسوم — حدود ثقة غير مكتملة
راجع `docs/agents/A1_FEE_SIGNATURE_TRUST_BOUNDARY_AR.md` والاختبارات `tests/test_a1_fee_signature_boundary.py`. وجدت Ed25519 للسجل المؤسسي لقواعد الإنتاج وHMAC لسياسات G5؛ لكنها ليست تحققًا صالحًا لبند رسوم مرتبط بعقد/إصدار/فقرة. لا تفعّل الثقة بمجرد `WrittenAuthorization` أو الموافقة في الواجهة، ولا تغيّر `NOT_VERIFIED / NOT_AUTHORIZED`. التالي: مراجعة مؤسسية لمخطط payload موقع وربطه بسجل مفاتيح موثوق وإبطال وصلاحيات، ثم تكامل محدود منفصل.


## DECISION-A1-GOV-20261018 — تفويض السوبر أدمن واعتماد إداري خارج النظام
**قرار مالك المشروع — معتمد كسياسة مستهدفة للتسليم، ولم يُنفذ بعد كصلاحيات تقنية.**
1. تعليق تطوير/فرض آلية التوقيع الإلكتروني المؤسسي **الخاصة بمراجع رسوم A1** في هذه المرحلة. يُعاد النظر فيها فقط إذا نشأت حاجة تشغيلية معتمدة في مرحلة متقدمة.
2. بعد تهيئة النظام وتسليمه للجهة، تُحصر جميع عمليات **إضافة وإدخال وتعديل وحذف أو اعتماد** البيانات المرجعية الحساسة (العقود وإصداراتها وملحقات الرسوم والتعرفة وسائر مرجعيات الإدارة) بحسابات دور `super_admin` المخوّلة حصريًا. سائر الأدوار قراءة/مراجعة وفق صلاحياتها بلا كتابة للمراجع. لا يعني ذلك منح السوبر أدمن سلطة تجاوز سجلات عدم القابلية للتعديل أو إعادة كتابة العقود المعتمدة؛ يظل التعديل بإصدار وتاريخ أثر مسجلين.
3. يتولى السوبر أدمن خارج النظام التوقيع/الموافقات المؤسسية والإجراءات الإدارية ويكون مسؤولًا عن قانونيتها وصحة إدخال المرجع المعتمد. داخل النظام يجب إبقاء هوية المنفذ وسجل التدقيق وبصمة المستند وتاريخ وإصدار المرجع، دون الادعاء بأن النظام تحقق تشفيريًا من التوقيع الورقي أو الخارجي.
4. **لا يُعطل هذا القرار ضوابط الأمان الحالية ولا يسمح بالتحايل عليها**: أنظمة G3/G5/ReferencePoint التي تشترط WrittenAuthorization أو توقيعًا أو مراجعة مستقلة أو تمنع اعتماد الإنتاج تستمر كما هي إلى أن تُراجع رسميًا آلية التشغيل البديلة ويُنفذ تغيير حوكمة منفصل باختبارات قبول. لا يمنح هذا القرار الصلاحيات فعليًا ولا يعتبر الإدخال وحده تفويضًا ماليًا.
5. موضع الفجوة المثبت: في `mcias/reference_api.py` تستخدم واجهات إنشاء العقود والتعرفة صلاحية `reference.write` وليس تحققًا صريحًا من `super_admin`؛ لذلك **تطبيق الحصر على مستوى API والسياسات ومنح الأدوار** (لا إخفاء أزرار الواجهة فقط) واختبارات منع الدور العادي وفعالية سجل التدقيق شرط قبول مستقل عند التهيئة/التسليم.
6. A1 يواصل التحليل للقراءة فقط، وتظل نتائج الرسوم غير ذات الدليل `NOT_VERIFIED` / `NOT_AUTHORIZED`. لا يبدأ مشروع توقيع أو A2 بسبب هذا القرار.

**نقطة الاستئناف:** لا تكرر بناء آلية توقيع رسوم الآن. عند بدء مرحلة التهيئة للجهة، راجع جميع المسارات القابلة للكتابة والـRBAC وعبور المستأجرين واختبر حصر الكتابة بالسوبر أدمن والنسخ المتعاقبة والتوثيق؛ لا تغيّرها ضمن PR20 بلا مهمة صريحة.


## A1 safeguard after deferring institution-signature workflow
Synthetic source-declared fee items must keep G6 review packet as provisional HUMAN_REVIEW, propagate approved_contract_fee_clause missing, and never invent signed G5 policy, reviewer decision, or G7 realized savings. This is only a test guard. Super-admin-only restrictions remain a handover policy pending separately authorized server-side enforcement.


## Next A1 checkpoint — itemized evidence
A small G2/G4/A1 encrypted original synthetic test suite checks line Decimal arithmetic, row SHA/locator attribution, missing price fail-closed, G6 HUMAN_REVIEW and G7 no savings; file `tests/test_a1_itemized_decimal_provenance.py`. This establishes no OCR clinical accuracy or authority to identify which of quantity/price/total is erroneous. Continue only after exact-SHA CI, without institutional signing, RBAC migration or financial policy changes.


## CI regression correction — synthetic invoice_total fixture
Exact-SHA run 39136573522 FAILED six new test cases; all classified MISSING_ATTACHMENTS, because the new CSV synthetic row wrote only line_total while header required both line_total and invoice_total. The source validator correctly rejected an incomplete row. Corrected the fixture to supply the *same stated amount* in both explicit columns; no changes to G2/A1 engines or missing-evidence rules. Next verify exact new SHA unit tests and source refs. 


## Tested limitation — original price missing
The six-case synthetic suite exposed that missing `unit_price` is fail-closed at `build_a1_snapshot` (`A1SourceBlocked`) rather than a G6 HUMAN_REVIEW packet. This is a real adapter gap, not a passed human-review acceptance criterion; preserve fail-closed and implement missing-input triage only in a separately tested follow-up. All complete rows still require verified SHA and arithmetic evidence.


## CHECKPOINT — 2026-10-18 unified input/audit requirements synchronization
Read owner-approved docs/MCIAS_UNIFIED_INPUTS_AUDIT_REQUIREMENTS_AR.md at 808a70806e6c5931b4dd5f7110e4c4d1a0a6b63e, plus related input clause triage and DG-001 branch notes; see docs/agents/A1_UNIFIED_INPUTS_IMPACT_AR.md. A1 needs service-date versioned contract/category/beneficiary-family/coverage/limits reads, no double count, append-only original/version lineage and shared tenant-safe audit events. These are **dependencies, not implemented capabilities**. Do not import unmerged PR22/PR25 code or create separate authorization/audit engines. Keep G2 invoice arithmetic and G6 HUMAN_REVIEW running. Previous SHA dfa4b9ab CI all workflows successful. Institutional digital signing remains deferred; super-admin-only reference edits is handover policy pending implementation. Next: verify CI on new SHA, resume missing-price fail-closed human review triage as separate scoped stage1 work.


## DG-001 — Documentation closure, latest-source SHA audit (2026-10-20)
**Inspection baseline:** PR20 HEAD `b536a94adf4d190ac48856bd435a8a624f3931f4` (open/Draft). This is the last *tested source snapshot*, not the new documentation commit SHA.
- G1–G7 `39142017085` PASS: 443 passed, 19 skipped, 1 warning — https://github.com/overurdream-collab/test2/actions/runs/39142017085
- Traceability `39142017105` PASS — https://github.com/overurdream-collab/test2/actions/runs/39142017105
- G9 `39142017076` PASS — https://github.com/overurdream-collab/test2/actions/runs/39142017076
- Enterprise `39142017100` PASS: 461 passed, 1 skipped, 14 warnings — https://github.com/overurdream-collab/test2/actions/runs/39142017100
- A1 model/rules `39142017152` PASS: 66 targeted pytest, 1 warning; 18 deterministic synthetic cases TP7/FP0/FN0/TN2 +9 abstentions; 36 Qwen3-8B synthetic model inferences TP10/FP0/FN0/TN26, mean 9.21275556 s per claim, peak RSS 9170036 KiB — https://github.com/overurdream-collab/test2/actions/runs/39142017152
Historical 57-test targeted snapshot, prior synthetic Qwen mean 9.51933 and the earlier negative 26-example model result remain unchanged in `STATE_A1.json` and earlier worklogs; datasets and test scopes differ. No fresh blind expert-labeled Arabic/English OCR/clinical documents or production claims were tested.
**Open acceptance barriers:** no signed/authorized effective-date G3/G5 unit tariff or additional fee authority; no independent clinical performed-service/Palermo proof; PDF/OCR evidence cannot bypass G2/A1 trusted-source contracts; missing-price fail-closed remains distinct from a functioning G6 triage; G6/G7 final human governance absent; PR22/23, Shared Audit, and production RBAC integrations require independent authority. Under the user-approved administrative policy, super-admin reference control is a *handoff intention*, not enforcement. **No financial or production acceptance.**
**SHA freshness:** each documentation edit changes the Git SHA; do not call old b536 CI a test of the newly committed HEAD. Recheck HEAD and only report fresh CI that exists and completes on it.

## DG-001 — HANDOFF-20261021-405 — E4 bridge continuation

Parent PR20 `6af41a04cf887d389656c9ce7ffc4e03b396b5a4`؛ استأنفنا عائق native enriched locator وmissing-price الموضحين أعلاه. العقد الإضافي المعتمد وmanifest الأربعة في `docs/E4_A1_BRIDGE_AR.md`؛ logs في `docs/engineering/worklogs/A1_2026-10-21_integration.md`.

`build_a1_snapshot` يعيد source_evidence قابلًا لإعادة التحقق مستقلًا دون analyze؛ native source_scope القائم يحمي CLAIMS/full metadata؛ `unit_price` الفارغ يخرج safe review لا سعرًا مشتقًا. يبقى qualified=false وunit_price_authority=NOT_ESTABLISHED حتى approved arithmetic rule وسياقadjustments؛ لا حكم مالي. source hash ليس تصديقًا. parent-reported PG16 4/4 على تركيب pinned مستقل موضح بالتقرير، وليس اختبار الفرع الكامل. لا OCR/model qualification جديد.

المشرف وسع ملكية A1 تقنيًا في workflow لمنع Qwen3-8B التلقائي على adapter PR: model job = workflow_dispatch فقط، وdeterministic checks كاملة على PR. لم نشغّل manual dispatch. baseline19 PASS، focused30 PASS؛ نتائج regression/traceability الأحدث في worklog405. الخطوة التالية: المشرف يثبت evidence التكامل على SHA المركب، وينشر Draft20 ويراقب CI على SHA التسليم نفسه؛ G5/G3 يملكان حجب سلطة الحساب وسياقه حتى الإثبات، ولا Merge/Deployment.

إغلاق تجربة regression الواسعة: على مصدر `6aca20dedbd4bcc7f18f9f4737bb9f1da6cc1f27` أعاد المشرف `PYTHONPATH=. /workspace/security-venv/bin/python -m pytest -q tests/test_a1*.py tests/test_traceability.py` بصلاحيةnetwork.enabled؛ **110 PASS في13.89s**، XML `/tmp/a1-root-regression.xml` (suite13.833s،110 tests،صفر failures/errors/skipped). التعليق المحلي السابق لم يتكرر؛ سببه ما زال غير محسوم. لا إعادة اختبار أو تغييرruntime/tests في هذا الإغلاق التوثيقي. Traceability6aca:35 commits/33 tracked/0 violations. تنبيه consumer: output_fingerprint يتضمنcreated_at؛ فصل trace hashes عن snapshot idempotency مسؤوليةG5، وعمله واختبارRED ما زالا لدىالمشرف، ولا ننسب إغلاقهما لنجاحA1. التالي نشرDraft20 علىHEAD التوثيقي معguardاليدوي نفسه، ثمCI علىSHAالمطابق.

### DG-001 — dependency follow-up405

نُقل إصلاح مالكsecurity منPR33/source `6454b6d054591e398c7251af5454c067fa00fc59` بعد فشلDependencyAudit الفعلي علىPR20 المنشورc9a98ae. قيدPillow13.0.0<14؛ script/test المنسوخان وبصماتهما وwiring المحدود في `docs/E4_A1_BRIDGE_AR.md`، وكلالعملياتفيworklog405-06/07 ومايليهما. توافقPillow13/OCR/images/scannedPDF/reports:32 PASS في5.09s؛ realdependency audit علىالشجرةالجديدة مازالينتظرCI بعدالنشر. لاignoreCVE أوexternaldependency exclusion؛ لادلالاتA1 أوworkflowQwen تغيرت. parent المحلي19c9fb0،parent النشرc9a98ae وفقمسارالمشرف؛لاreset/rebase/pull. التالي: تسليمCommit/tree للمشرف لنشرDraft20 ومراقبةDependencyAuditالحقيقي علىSHAالمنشور.

### DG-001 — Enterprise runner Tesseract prerequisite

علىHEADالمنشور `fca4707b88366f175e8928d7136bd1badd7ca4e2` نجحDependencyAuditالحقيقي60external/0vulns وcompat32PASS وبقيةالفحوصالمبلغعنها؛فشلEnterprise39676632722/job119488076413 بحالتينFileNotFoundError:tesseract،مع472PASS/1SKIP. أضيفتخطوةapt-get update/installtesseract-ocrالقائمةنفسهافيPR33/test2 بعدتثبيتPythondependencies وقبلfullcombinedtest فيworkspace.yml،دونتغييراختباراتأوتوقعات. لمتُعدcompatأوauditالناجحة؛CIعلىالشجرةالجديدةينتظرنشرroot ومتابعةEnterpriseالفاشل. parentالمحليba98c27 وparentالنشرفca4707 موثقانفيworklog405-10/11/12؛لاreset/rebase/merge/deployment.
