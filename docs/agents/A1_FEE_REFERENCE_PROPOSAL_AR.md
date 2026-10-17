# A1 — مقترح عقد بيانات مرجع الرسوم الإضافية v1

**الحالة:** DRAFT_ONLY — لا يولد سعرًا معتمدًا ولا سياسة G5 ولا `allowed_fees` تشغيليًا.

## إعادة استخدام البنى الموجودة
- G3 `ContractVersion`: `organization_id`, `provider_code`, `id`, `version`, `effective_from`, `effective_until`. `ProviderTariff` هو تعرفة **خدمة** ولا يصح استخدامه لتصريح رسم إضافي.
- PR #22 `ReferencePoint`: مرجع نص/تاريخ/مقدم/مصدر اختياري، غير مدمج مع A1 ولا يحدد هوية العقد، وحدة الرسم والتوقيع المؤسسي الملزم.
- PR #23 `Contract Intelligence`: اقتراحات مستخرجة ومثبتة الموضع لكنها `DRAFT_ONLY`؛ لا اعتماد آلي.

## المخطط المقترح
النموذج `ProposedAdditionalFeeReference` في `mcias/agents/a1_fee_reference_contract.py` يقدم: المؤسسة، مقدم الخدمة، `contract_version_id` و`contract_version`، رمز الرسم، `unit`، `unit_price` كـDecimal string دقيق، `currency`، `effective_from` و`effective_until` بنطاق نصف مفتوح، `clause_source` ببصمة SHA-256 ومعرف الملف وموضعه، `reference_point_id` اختياري، وبيانات `institutional_signature` المرجعية وحالة مراجعة.

**هام:** `institutional_signature.verification_status` محصور بـ`NOT_VERIFIED` و`financial_authority=NOT_AUTHORIZED` حتى لو كانت بيانات التوقيع مملوءة. Pydantic يتحقق من *شكل* البصمة والتاريخ والقيمة؛ ولا يثبت ملكية العقد أو صحة توقيع أو مطابقة البايتات أو سريان تفويض مؤسسة. لا يوجد ORM/ترحيل/واجهة/تفعيل في هذا التغيير.

## شروط استعمال مستقبلية فقط
ربط FK بالعقد الساري للمؤسسة ومقدم الخدمة ومطابقة مرفق بند الرسوم، إثبات البايتات الأصلية وموضع الفقرة، تحقق توقيع مستقل مربوط ببصمة المحتوى والعقد والإصدار، منع تعارض الإصدارات، مراجعة بشرية وصلاحية مؤسسية، ثم مراجعة تكامل G3/G5/PR22/23. عند عدم توافر ذلك تبقى `approved_contract_fee_clause` ناقصة الدليل.

## التحقق
`python -m pytest -q tests/test_a1_fee_reference_contract.py`

جميع الاختبارات اصطناعية؛ لا رسوم فعلية أو بيانات مرضى أو سير دفع.


## مطابقة للقراءة فقط
تقدم `ReadOnlyContractAnchor` هوية نسخة عقد G3 المقروءة ومصدر بند الرسم. `match_proposed_fee_read_only` تقارن المؤسسة ومقدم الخدمة ومعرف العقد وإصداره والحالة approved والفترة نصف المفتوحة وموضع المصدر وبصمته. حتى `matching=true` يعيد `signature_verification=NOT_VERIFIED` و`financial_authority=NOT_AUTHORIZED`. لا دليل على صحة توقيع مؤسسي أو بايتات الأصل، ولا استعلام أو كتابة قاعدة بيانات ولا ربط تلقائي بـ PR22/23.
