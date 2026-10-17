# A1 DATA CONTRACT — الربط المرحلي مع G2/G4
**الحالة:** P0 تجريبي/قراءة فقط، CSV وXLSX موثقان صناعيًا، واجهة GET Preview معطلة افتراضيًا ومحظورة في الإنتاج. **النسخة:** mcias.a1.input.v1.
التنفيذ: mcias/agents/a1_trusted_input.py. لا API إنتاجية مفعلة ولا تشغيل على مطالبات حقيقية، ولا نقل PHI أو اعتماد إنتاجي.

## ما ثبت من فحص نماذج النظام
ClaimEntry يخزن خدمة واحدة ومبلغًا إجماليًا. ProviderTariff.amount بلا unit ولا يمكن اعتباره سعر وحدة. ReferencePoint وContract Intelligence في PR #22/#23 غير مدمجين ولم يثبت توقيعهم كسياسة مالية. لا يخترع الوكيل وحدة أو تقسيمًا للمبلغ.

## العقد
- org من actor موثوق، run_id، timestamp UTC، schema_version.
- claim: id, tenant_id, provider_code, service_date, currency, amount, source.
- invoice: id, tenant_id, currency, stated_total, items: id/kind/code/unit/quantity/unit_price/line_total/source.
- source: document_id وSHA-256 والموضع row؛ المصدر موجود فعلًا في G2 ويحفظ بايتاته مشفرة.
- source_verifications: original_sha256_verified وextracted_rows_equal_original.
- missing_evidence لا يحوَّل إلى PASS. نموذج Pydantic يرفض extra fields وNaN/Infinity/float/precision فوق أربع خانات والعملات والمؤسسات المتعارضة.
- contract/reference: G3 مبلغ تاريخي diagnostic بصفة REFERENCE_ONLY_UNIT_UNPROVEN؛ لا توجد تعرفة وحدة معتمدة ولا G5 policy fingerprint موقعة، لذا A1 لا يقارن زيادة سعر الوحدة تلقائيًا.

## سلسلة المصدر الفعلية
G4 ClaimEntry + ClaimBatch → G2 IngestionDocument/SourceFile/EncryptedStore → SHA-256 من بايتات الأصل → إعادة قراءة CSV بـG2 csv_parser.parse → مطابقة كل صف وموضع بمستند G2 ExtractedSourceRecord → ربط ClaimAttachment بفاتورة CSV بمفاتيح claim_reference/provider/currency → A1Input.model_validate → analyze بدون نموذج AI.
إذا كانت الفاتورة PDF/صورة أو ناقصة أو متعددة نسخ أو تحوي حقلًا غير موثق، يرجع تعليق/نقص أدلة؛ لا يدّعي دعمها في هذه المرحلة. لا تسجل تسوية مالية.

## الصلاحيات
يجب أن يكون actor من جلسة خادمية حقيقية وactive ومن نفس مؤسسة ClaimEntry؛ requires claims.read وingestion.read وصلاحيات medical_fields.<column>.read لكل عمود مقروء. لا يسمح للمستدعي باختيار org_id. لا تستخدم attested=True من العميل.

## مفتوح
Palermo تحقق مستقل من مصدر تنفيذ الخدمات الطبية والصفحات العربية/OCR وPDF، اعتماد وحدة تعرفة مؤسسية وربط G5 الموقّع وPR22/PR23/G6/G7 لم تستكمل. XLSX أثبتت فنيًا على عينات اصطناعية ولا تعني التحقق السريري أو قبول مستندات حقيقية. لا تثبت وثائق أو اختبارات هذا الفرع استخدامًا إنتاجيًا.

## أوامر
python -m pytest -q tests/test_a1_trusted_input.py tests/test_a1_invoice_integrity.py
python -m pytest -q


## واجهة HTTP تجربة فقط
تمت إضافة GET /api/v1/a1/claims/{claim_id}/preview خلف feature flag MCIAS_A1_PREVIEW_ENABLED=true وبشرط MCIAS_ENVIRONMENT != production. يتطلب توثيق bearer session وصلاحية claims.read + ingestion.read + صلاحيات كل حقل Invoice. الواجهة افتراضيًا 503 ولا تسمح بالنشر إنتاجيًا، وتعيد 404 عند عدم صلاحية/وجود المطالبة و409 عند فشل سلامة المصدر، ولا ترسل البيانات إلى نموذج AI أو قاعدة مالية.
اختبار HTTP: python -m pytest -q tests/test_a1_preview_http.py. لا ترفع feature flag على خادم حقيقي؛ مستخدم فقط لبيئة تطوير اصطناعية منفصلة.


## XLSX (مع إثبات البايتات)
يقبل adapter الآن CSV وXLSX الأصلية فقط: يمر ملف XLSX أولاً عبر G2 file_scanner ثم G2 isolated_parse المحدود (عملية منفصلة)، ثم يطابق كل صف وموقع sheet/row مع ExtractedSourceRecord ويحفظ بصمة البايتات. الصيغ والحجر والمحتوى غير الآمن تفشل مغلقة. PDF/image OCR غير مؤكد البنود؛ لا دعم مالي مفترض. الاختبار: test_actual_xlsx_invoice_matches_encrypted_original_with_sheet_row (synthetic).


## تحقق مستقل من المطالبة نفسها
يُعاد تطبيع صف المطالبة الأصلي المحمي بواسطة G4 claim_normalization.normalize، ثم يُقارن بكل حقول ClaimEntry (provider, service, date, original amount/currency, beneficiary token, claim_reference)، وليس SHA الملف وحده؛ أي اختلاف مباشر في قاعدة بيانات الاختبار يُوقف A1 قبل التحليل. صلاحيات الحقول تشمل أعمدة G4 الأصلية كذلك. اختبار synthetic يستخدم UPDATE في SQLite مؤقتة للتحقق من guard، لا يتصل بقاعدة حقيقية.


## مرحلة 1 — نوع البند من أصل الفاتورة (تكامل صغير)
يمكن لملف CSV/XLSX يحتوي حقول G2 الموثقة أن يضيف عمودًا اختياريًا `item_kind` بقيمة `service` أو `fee`. ينتقل النوع من صف البايتات الأصلية بعد إعادة الاستخراج والتحقق، ولا يستنتج المحوّل رسمًا من `service_code` أو من المبلغ. الصفوف القديمة التي لا تتضمن العمود تبقى `service` للتوافق، ووجود قيمة غير معروفة يؤدي إلى `invalid_invoice_row` و`INSUFFICIENT_EVIDENCE` دون تسوية مالية. لا تتحول الرسوم إلى `UNJUSTIFIED_FEE` محسومة بلا جدول رسوم عقدي مُعتمد بالكامل.

اختبارات: `test_original_invoice_explicit_fee_kind_is_preserved_without_financial_authority` و`test_invalid_declared_fee_kind_fails_closed_not_silently_service`. هذان اختبارا أصل CSV مشفر اصطناعي؛ لا إثبات لتصنيف رسوم من OCR/PDF.


## رسوم العقد — شرط إثبات مرجع البند (مرحلة 1)
حتى مع `item_kind=fee` وسجل في `allowed_fees`، لا يعتبر A1 الرسم مطابقًا إلا إذا احتوى **بند الرسم المسموح** على `source: {document_id, sha256, locator}`، وكان `document_id` و`sha256` متطابقين مع مصدر العقد الساري المعتمد. عند غياب/اختلاف ذلك، يصدر `FEE_CONTRACT_AUTHORITY / INSUFFICIENT_EVIDENCE` مع `approved_fee_clause_source` ولا يُحتسب الرسم مسموحًا به. مرجع العقد وموضع البند هما إثبات بنيوي استشاري، **لا تحقق بايتات العقد أو توقيع المؤسسة**؛ ربط G3 الحقيقي بوحدات ورسوم مصدقة يظل معلقًا. اختبار الخدمة/الرسم لم يغيّر بوابات الأحكام المالية.
