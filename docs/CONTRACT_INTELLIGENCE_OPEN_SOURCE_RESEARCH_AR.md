# Contract Intelligence — بحث مفتوح المصدر قبل التطوير (2026-10-17)

## الحالة والحدود
Research-first GATE R0 — مكتمل كمسح مستودعات رسمية وتراخيص وفحص كود MCIAS وتجارِب محلية محدودة؛ **لم** تُشغّل مشاريع Docling/MinerU/PaddleOCR/Unstructured/Marker/OCRmyPDF داخل هذه البيئة، ولم تُشغّل نماذج LLM حقيقية. أي تصنيف أدناه **قرار غربلة وليس شهادة جاهزية إنتاجية**. مصدر الحقيقة هو branch feat/mcias-contract-intelligence فوق PR #22 DRAFT؛ لا تتغير main أو بيانات مؤسسة.

## نتائج جرد MCIAS من الكود لا من README
- mcias/ingestion/reader_agent.py: موجه حقيقي قائم لأنواع CSV/XLSX/PDF/image؛ لا تُبنى طبقة ingestion ثانية.
- ingestion/parsers/pdf_parser.py: pypdf صفحة بصفحة، fallback OCR اختياري Tesseract في حال صفحة بلا نص؛ النص الأصلي لا يحتفظ بنطاقات/إحداثيات دقيقة أو علاقات جدولية؛ الصفحات الممسوحة غير الواضحة تُحجر.
- ingestion/parsers/excel_parser.py: openpyxl read_only، منع الصيغ، حد 50 sheet / 256 عمود / 100k صف، مصدر sheet-index/row؛ يحتفظ قيم الخلايا كسلاسل.
- ingestion/ocr_engine.py: Tesseract CLI محلي، لغة MCIAS_OCR_LANG الافتراضية eng، حد 20 ثانية و20M pixels؛ دعم العربية يتطلب ara محليًا.
- ingestion/orchestrator.py: hash SHA256 + dedup داخل المؤسسة + EncryptedStore + isolate parser + Palermo-1 + manifest + سجل extracted_source_records + مراجعات حجر؛ لا يجوز تجاوز malware scanner.
- models_reference_points.py/reference_points.py + migration 0019: نسخ مسودة/اعتماد مؤرخة بنطاق المؤسسة، immutable original، closure append-only؛ لا يوجد جدول AI proposals ولا مراجعة مسودات AI حتى هذه اللحظة.
- reference_rule_bridge.py + G3/G5: قراءة توفيق تحفظ سلطة التعرفة وسياسة audit المالية الأصلية؛ لا تفعيل من AI.
- مسح شجرة git: لا ملف AI Model Gateway/LLM serving موجود؛ لا تستنتج endpoint جاهز. قائمة dependencies الأساسية فيها pypdf/openpyxl/PyMuPDF/Pillow؛ لا تضاعفها.
- Docs DG-001: كل commit يحتوي HANDOFF جديدًا + CURRENT_STATE، مع PENDING_CI حين لم يتم فحصه.

## المقارنة التتبعية — نسخ كما ظهرت في GitHub 2026-10-17
| الأصل الرسمي | إصدار / commit مرصود | ترخيص ومخاطر تجارية | الوظيفة واللغة والجداول | تشغيل/تكلفة/تكامل | تصنيف مبدئي |
|---|---|---|---|---|---|
| [Docling](https://github.com/docling-project/docling) | v2.140.0 بتاريخ 2026-10-16؛ 0e54294231b69bc2cf7a39873235495788f76b57 | MIT للكود؛ تدقيق تراخيص أوزان OCR/layout التابعة شرط | PDF/Office/structured tables/locators. Tesseract يمكن اختيار ara + eng؛ جودة العربية ليست مقاسة لدينا | CPU ممكن لكن ML ثقيل بحسب pipeline؛ أدرجه كمحوّل إضافي معزول لا كبديل G2. تنزيل أوزان محلي فقط | ADAPT (NOT TESTED) |
| [MinerU](https://github.com/opendatalab/MinerU) | mineru-4.0.12-released 2026-10-11؛ b7f3dd0c5f6e6d66a298239ffd02b328b873918e | LICENSE مخصص MinerU Open Source License بمتطلبات إضافية، **ليس Apache خالصًا**؛ يحتاج مراجعة قانونية لإعادة التوزيع | PDF/Office/XLSX والجداول متعددة الصفحات وOCR متعدد اللغات حسب release notes؛ لا دليل دقة عقودنا العربية | Python/ML، قد يتطلب GPU/تنزيل أوزان كبيرة؛ بيئة منع تنزيل الأوزان حاليًا | REFERENCE ONLY (NOT TESTED) |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | v3.7.0 2026-06-11؛ dab3fe35379033fdcb2d0e9572fac0b36c9a9ebf | Apache-2.0 للكود؛ راجع كل وزن فرعي | OCR متعدد اللغات وPP-Structure؛ العربية تحتاج اختيار النموذج والتحقق، tables layout candidate | مكوّن احتياطي عند تدهور OCR Tesseract؛ Runtime Paddle متطلب إضافي CPU/GPU غير مثبت | REUSE COMPONENTS (NOT TESTED) |
| [Unstructured](https://github.com/Unstructured-IO/unstructured) | 0.27.28 بتاريخ 2026-10-16؛ 1b02b4d189c260ed9b1aca29583203e233d853cb | Apache-2.0 للمستودع، راجع اعتماد أدوات خارجية والخدمات الاختيارية | partition PDF/XLSX/DOCX، strategy hi_res وocr_only، اللغات عبر حزم Tesseract؛ هيكلة الجدول تحتاج مراجعة | قدرات كبيرة لكن dependencies ثقيلة؛ المدمج pypdf/openpyxl يكفي للمسار السهل | ADAPT (NOT TESTED) |
| [Marker](https://github.com/datalab-to/marker) | v2.0.0 2026-07-20؛ ad1b414d846653f4048cdc527993f6c09b829869 | الكود Apache-2.0 حاليًا **والأوزان modified AI Pubs Open Rail-M** بقيود تجارية حسب حجم الجهة؛ لا تفترض سماح التوزيع | PDF→Markdown/JSON وجداول، LLM hybrid؛ العربية غير مثبتة محليًا | PyTorch ونموذج وزن كبير؛ Hybrid افتراضي خارجي غير مقبول لملفات حقيقية | REFERENCE ONLY (NOT TESTED) |
| [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) | v17.13.0 2026-09-28؛ cf0df3da06aef04fe9a5bf91c6feff36370bb3eb | MPL-2.0؛ تعديل ملفات كوده يلتزم أحكام المصدر؛ Ghostscript/Tesseract تبعيات مستقلة | يصنع طبقة نصية PDF؛ لا يستخرج بنودًا أو بنية جداول؛ ara+eng عبر Tesseract حسب packs | CPU وقابل للتشغيل على premises، لكنه زائد الآن مع OCR adapter G2؛ لا تغيير G2 قبل benchmark | REUSE COMPONENTS عند الحاجة فقط (NOT TESTED) |
| [MCIAS pypdf/openpyxl/Tesseract](https://github.com/overurdream-collab/test2/tree/feat/temporal-reference-inputs-and-four-outcomes/mcias/ingestion) | PR #22 baseline b694a2a1603a9a4c6d7af26ed56035b1a28b0166 | المكتبات الموجودة + التراخيص حسب packages؛ راجع SBOM قبل التوزيع | PDF نصي + XLSX أسطر + Tesseract OCR مع source locator؛ يفتقد layout/normalization clauses | صفر بنية إضافية؛ مسار G2/tenant/crypto/Palermo-1 قائم بالفعل | READY TO INTEGRATE (مراد: مدمج بالفعل؛ تحتاج إعادة قياس كاملة) |

### نشاط/issues وPRs المرصودة (ليست نتيجة اختبار)
- Docling pushed_at 2026-10-16؛ issue #4872 تجاهل MLX Whisper temperature.
- MinerU pushed_at 2026-10-17؛ issue #5648 crash TextSpan superscript/subscript.
- PaddleOCR pushed_at 2026-09-16؛ issue #18397 أعمدة PDF متعددة الصفحات مفقودة في PP-Structure.
- Unstructured pushed_at 2026-10-16؛ issue #4557 تصنيف عنوان DOCX ملتبس.
- Marker pushed_at 2026-10-14؛ issue #1121 تكرار/غياب shards.
- OCRmyPDF pushed_at 2026-10-12؛ issue #1769 --redo-ocr قد يزيل بعض النص المرئي.
- هذه bugs معروفة تستلزم الانتباه، لا إثبات أنها تؤثر على الإصدار المثبت في MCIAS. اطلع على /issues و/pulls وCI لكل tag مختار قبل الترقية.

## فحص عملي مستقل محدود بتاريخ 2026-10-17
البيئة الحالية منفصلة عن مستودع GitHub ولا تستطيع clone/download packages بسبب DNS (git clone: Could not resolve host: github.com). ليس هناك Ollama ولا transformers ولا Docling/Marker/MinerU/PaddleOCR مثبتة. التقنيات المتاحة محليًا pypdf/openpyxl/PyMuPDF/Pillow/reportlab/Tesseract/PyTorch.
اختبارات تجريبية **بمستندات SYN فقط** عبر /mnt/data/ci_research_tests/probe.py (هذه مسارات بيئة مؤقتة وليست أدلة مستودع قابلة لإعادة التشغيل):
1. PDF نصي من صفحتين ReportLab: pypdf نجح في استخراج CONSULT H1 5000 YER في صفحة 1 وH2 7000 YER في صفحة 2، 2/2 حقائق مستهدفة بسيطة فقط؛ ليس Precision/Recall للبنود.
2. صورة PNG اصطناعية إنجليزية: tesseract -l eng → CONSULT H1 5000 YER (exit=0). لا يقيس حالات OCR الصعبة.
3. XLSX صناعي ثلاثة مقدمي خدمة: artifact_tool أنشأ المصنف (3475 bytes)؛ لم يُجر اختبار استيراده عبر موديول MCIAS لأن clone repo لم يتوفر محليًا.
4. Tesseract لديه ara installed، لكن لم يُختبر بند عربي ولا OCR لجداول عربية.
5. لا تشغيل GPU inference، ولا benchmark بين 6 مشاريع، ولا اختبار درجات دقة من datasets؛ كلها PENDING/NOT_RUN وليس PASS.

## نماذج AI المرشحة — لا اختيار نهائي حتى تجربة فعلية
- [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) Apache-2.0، نص عربي/إنجليزي وstructured JSON مرشح أول للتجربة عبر endpoint محلي متوافق OpenAI. الأوزان bfloat16 نحو 8GB حسابيًا، الذاكرة الكلية أعلى ومتغيرة؛ quantization قد تخفضها مع خسارة جودة غير معروفة. **لم يُشغّل** ولا إثبات precision بعد.
- [Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) Apache-2.0، VLM مرشح لصفحات ممسوحة بعد تبرير؛ استهلاك GPU أكبر حسب حجم الصور؛ ليس افتراضيًا.
- [granite-docling-258M](https://huggingface.co/ibm-granite/granite-docling-258M) Apache-2.0، layout/doc understanding صغير، لا نفترض دعمه العربي الدقيق قبل benchmark.
- [CUAD](https://huggingface.co/datasets/theatticusproject/cuad) CC-BY-4.0 بيانات عقود قانونية إنجليزية (41 فئة) تصلح لبحث التصنيف العام مع الإسناد، لكنها ليست تعرفة طبية يمنية ولا تغطي عقودنا العربية؛ اختبارنا الأساسي يجب أن يكون corpus اصطناعيًا محليًا ولا يدخل بيانات مرضى/مؤسسات.
- لا اختيار لقاعدة سحابية أو Colab لبيانات حقيقية؛ اختبار اصطناعي فقط وفق الشروط. لا توجد GPU/خدمة نموذج MCIAS مثبتة بالمستودع. Ollama/vLLM خيارات تشغيل لا نثبّتها بلا ضرورة.

## القرار R0
**إعادة استخدام G2 وpypdf/openpyxl وOCR الحالي هي نقطة البداية الأقل خطرًا**. يُفصل Contract Intelligence كطبقة AFTER Palermo-1 تستهلك extracted_source_records، وتستدعي استدلال نموذج محلي configurable only، وتطبّق evidence matching deterministic قبل إنشاء draft. إن فشل النموذج/لم يوجد: لا مقترح ولا تفعيل، وتُسجَّل الحالة. مكوّن Docling مسار اختياري للـtables عند إثبات فشل G2 + ترخيص أوزان + benchmark عربي. لا شيء يتحول تلقائيًا إلى G3/G5.
**بوابات معلّقة:** تشغيل LLM حقيقي on-prem، عينات عربية/mixed/scan، مقارنة مخرجات 2+ parsers على 20 ملفًا على الأقل، مراجعة تراخيص إصدار مثبت/SBOM، أمان endpoints، دقة قياسية gold، محرك التصاريح الموقعة.
