# A1 — بحث إعادة الاستخدام واختيار المكونات المفتوحة المصدر
**المرحلة R0:** 2026-10-17، قبل التعديلات الهندسية لهذه المهمة. **الحالة:** بحث مصادر وتحليل كود؛ لم تُثبّت أدوات OCR جديدة ولم تُقَس دقتها محليًا. الروابط أدناه للمستودعات/الوثائق الرسمية؛ الإصدارات المحددة يجب تثبيتها عند اعتماد أي تبعية.

## أولاً: جرد المكونات الفعلية لـMCIAS

| المكون | الموجود في الشيفرة | القرار | الحدود |
|---|---|---|---|
| G2 ReaderAgent | `mcias/ingestion/reader_agent.py`، parsers CSV/XLSX/PDF والصور، Palermo-1 وQuarantine وExtractedSourceRecord | **READY_TO_INTEGRATE** | قراءة PDF الممسوح تتطلب OCR محليًا؛ لا يُختلق رقم من OCR |
| تخزين الأصل | `EncryptedStore.get(object_id,digest)` يحسب SHA256 على البيانات المفكوكة | **READY_TO_INTEGRATE** | يجب تطابق SHA بين SourceFile وIngestionDocument وClaimAttachment وClaimBatch |
| G3 | ContractVersion وProviderTariff مع service_code/currency/amount وتاريخ السريان | **REUSE_COMPONENTS** | `ProviderTariff` لا يحوي unit، فلا يجوز اعتباره سعر وحدة الفاتورة |
| G4 | ClaimEntry: مبلغ إجمالي ورمز خدمة واحد وتاريخ ومصدر؛ ClaimAttachment/ExtractedSourceRecord | **ADAPT** | لا جدول بند فاتورة معتمد؛ استخدم records محفوظة من G2 فقط ولا تضع تمثيلًا مختلقًا |
| G5 | 8 فاحصين، `AuditPolicy`، `fingerprint_policy`، `resolve_grant` | **REUSE_COMPONENTS** | توقيع/منح سياسة مالية إلزامي؛ نتائج A1 لا تُدرج كخصم مالي |
| Palermo-2 | `mcias/palermo2.py::verify` لمراجعة G5 المالية | **ADAPT** | أضف تحقق أدلة منفصلًا لـA1؛ لا تغير توقيع وظيفته الحالية |
| G6/G7/G8 | مراجعة بشرية وتقارير وتحليلات | **REFERENCE_ONLY** حتى واجهة صلاحيات معتمدة | لا إدراج تعديلات محاسبية أو SavingsLedger |
| PR #22 | ReferencePoint / Closure / reconcile و4 نتائج أولية | **REUSE_COMPONENTS** مستقبلًا | Draft غير مدمج؛ لا تنقل واجهاته على أنها متاحة في فرع A1 |
| PR #23 | استخراج العقود ومقترحات تاريخية وtyped diagnostic | **REUSE_COMPONENTS** مستقبلًا | Draft مبني على PR #22، Draft لا يفعّل أسعارًا في G3/G5؛ لا تنسخ خدمة ثانية |
| Professor OS وAI Gateway | لا يوجد تنفيذ مثبت للواجهات المطلوبة في أشجار الفروع المقروءة | **REFERENCE_ONLY** | واجهة تجريبية منفصلة فقط، لا خدمة بديلة |

## ثانياً: المرشحون الخارجيون (المعلومات من المستودعات/الرخص، لم نختبر هذه الأدوات عمليًا في MCIAS)

| المشروع/الرابط الرسمي | الترخيص/الاستخدام التجاري بحسب المصدر | ملاءمة العربية/المعالجة/الموارد/التكامل | القرار |
|---|---|---|---|
| [pypdf](https://github.com/py-pdf/pypdf) | BSD-3-Clause؛ يعمل بلا GPU | موجود داخل G2 أصلًا، يحفظ صفحات PDF؛ لا يتعرف على مسح ضوئي وحده | **READY_TO_INTEGRATE** |
| [openpyxl](https://openpyxl.readthedocs.io/) | MIT؛ قائم بالفعل في G2 | ملفات XLSX مع locator sheet/row؛ عدم تنفيذ الصيغ | **READY_TO_INTEGRATE** |
| [Docling](https://github.com/docling-project/docling) | MIT للكود؛ رخص النماذج التابعة تُراجع منفصلة | جداول وتخطيط مستندات، PDF/XLSX، خيار مرحلة OCR المتقدمة؛ يتطلب قياس موارد وترخيص الأوزان | **ADAPT** لاحقًا |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | Apache-2.0 للكود؛ تحقق من كل وزن عند التثبيت | يدعم ar/en وفق [الوثائق الرسمية](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md)، أثقل من parser موجود، يتطلب تقييم أرقام عربية وعقود | **ADAPT** بعد gold OCR |
| [MinerU](https://github.com/opendatalab/mineru) | رخصة مخصصة مبنية على Apache-2.0 مع شروط نسبة الاستخدام التجاري والإسناد والحدود؛ ليست Apache خالصة | PDF/صور وتخطيط متعدد اللغات، متطلبات نماذج ثقيلة والتزامات قانونية إضافية | **REFERENCE_ONLY** لحين مراجعة قانونية |
| [Marker](https://github.com/datalab-to/marker) | قيود تجارية منفصلة على الأوزان ورخصة GPL/ازدواجية | تعقيد وترخيص غير مناسب للاستعمال المؤسسي دون فحص مستقل | **REJECT** الآن |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | AGPL-3.0 أو ترخيص تجاري | موجود في بعض تجهيز G2 الاختيارية؛ قبل توسيع الاستخدام التجاري يجب مراجعة التوافق القانوني | **REFERENCE_ONLY** |
| [Qwen3-8B-GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF) | Apache-2.0 في بطاقة النموذج؛ نموذج محلي | تشغيل فعلي مثبت في CI على CPU، ذاكرة ~10GiB؛ دقة 36 حالة اصطناعية ليست gold إنتاجية | **READY_TO_INTEGRATE** كمدقق نصي استشاري |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) و[llama-cpp-python](https://github.com/abetlen/llama-cpp-python) | MIT؛ JSON Schema / llama.cpp grammar | موجود في مسار Qwen الحالي، لا API خارجي ولا رسوم؛ اختبر schema وصفر ارسال بيانات | **READY_TO_INTEGRATE** |
| [Pydantic](https://docs.pydantic.dev/) / JSON Schema | MIT؛ موجود ضمن FastAPI الحالي | تحقق من حقول التنظيم والتواريخ والأعداد المالية والهوية، لا يتطلب نموذج AI | **READY_TO_INTEGRATE** |
| [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) | MPL-2.0 للكود؛ تعتمد الصور/GS/Tesseract على رخصهم | إثراء صور PDF بمحتوى OCR؛ لا يثبت الكمية الحقيقية أو صحة السجل | **REFERENCE_ONLY** |
| [Unstructured](https://github.com/Unstructured-IO/unstructured) | راجع LICENSE وإصدار التثبيت قبل الدمج | ميزات جداول/PDF عامة، قد يكرر G2 واستهلاك/تبعية أكبر | **REFERENCE_ONLY** |
| [vLLM](https://github.com/vllm-project/vllm) / [Ollama](https://github.com/ollama/ollama) | تُراجع الرخص المرفقة للإصدار المعتمد | تشغيل نماذج محلي بديل؛ حاليًا لا جدوى من استبدال llama.cpp CPU المثبت دون benchmark | **REFERENCE_ONLY** |

### حالة الاختبار والصيانة والأمان
- **تم فحص:** وجود مستودعات ومزايا منشورة ومعلومات الترخيص العامة، وإعادة استخدام كود MCIAS الحالي وأدلة CI القديمة. لم نشغّل Docling/PaddleOCR/MinerU/Marker/OCRmyPDF/Unstructured/vLLM أو نثبت أوزانها، لذا الدقة ومقارنة الموارد **NOT_MEASURED**.
- **الإصدارات:** لا تعتمد آخر إصدار تلقائيًا؛ اختبارات CI الحالية تستخدم متطلبات `pyproject.toml` للأدوات الموجودة. تبعيات جديدة تتطلب pin/review وSBOM وpip-audit وترخيص تجاري، ثم اختبار Arabic/English golden وPDF جدول/صورة مستقل.
- **الصيانة:** المشاريع المشار إليها تنشر شيفرة ووثائق ونشاط مجتمع ظاهر في GitHub وقت البحث؛ لم ننفذ فحص CVE شامل أو تدقيق حزمها، لذا الأمن لكل أداة جديدة **UNVERIFIED**.
- **خطر الترخيص:** رخص أدوات استخراج PDF مستقلة عن رخص أوزان النموذج أو Ghostscript؛ لا تقرر اعتمادًا تجاريًا قبل مراجعة قانونية.
- **القرار:** `Reuse → Adapt → Integrate → Build only when justified`. من غير الآمن استيراد OCR جديد لتجاوز مشكلة ثقة المرجع. أولوية A1 هي عقد typed على البيانات وقراءة مصدقة ومراجع زمنية لا تفترض الوحدة.

## ثالثاً: قرارات هندسية ملزمة لـA1
1. لا نسخ لـContract Intelligence؛ PR #23 Draft ومقترحاته لا تحل محل سياسة G3/G5 الموقعة.
2. لا تبدل G5 أو Palermo-2 المالي؛ أنشئ تحققًا محدودًا لـA1 يقرأ الملف الأصلي ويحسب SHA ويعيد نتيجة مستقلة غير مالية.
3. استخدم EncryptedStore الموجود وأصل G2 لا مسارات خارجية يقدمها العميل. لا تثق بعلم `attested=True` كإثبات خادمي حتى يثبت أصله.
4. عندما تكون الفاتورة إجماليًا بلا بنود ووحدة معتمدة، اكتب `INSUFFICIENT_EVIDENCE` ولا تختلق قيمة.
5. استخدم Pydantic القائم في dependencies، لا تعتمد ملفات sidecar لتحديد عقد أو سعر بدون سياسة موقعة.
6. أبقِ PR #20 Draft وأي تكامل مع #22/#23 مشروطًا بثبات الواجهات وعدم الدمج غير المصرح.
