# A1 — حدود التوقيع المؤسسي ومسار تكامل مرجع الرسوم

الحالة: **مراجعة كود + تصميم غير مفعل**. فرع PR20 فقط، دون تعديل G3/G5 أو دمج PR22.

## أدلة كود فعلية
- `mcias/authorization_signatures.py:verify_written_authorization`: Ed25519 يتحقق من بايتات مستند مع بصمة SHA-256 مفتاحية موثوقة تُمرر من جهة مستقلة. لا يُقرأ المفتاح من طلب المستخدم. لا ينفذ تحقق انتهاء صلاحية تفويض أو سحب صلاحية رأس المؤسسة بذاته.
- `mcias/production_authorization.py:verify_production_approval`: Ed25519 + ملف سجل مفاتيح وموافقات موثوق `MCIAS_AUTHORIZATION_REGISTRY` خارج طلب HTTP، مع حماية صلاحيات الملف. الرسالة الموقعة تربط `organization_id, approved_by, authorization_id, rule_id, source_id, source_sha256` لقواعد `RuleVersion`؛ **لا تحتوي fee_code أو contract_version_id أو unit أو clause locator أو فترة سريان بند الرسم**.
- `mcias/audit_authorization.py:verify_registered_policy`: HMAC لسياسة G5 مع fingerprint وموقّع ومراجع مستقل وصلاحيات حية وسحب المنحة؛ نطاقه سياسة G5 وليس تصريح رسم أو بصمة فقرة عقد.
- `mcias/reference_service.py:attach_authorization`: عقد G3 يحتفظ بسجل WrittenAuthorization لموافق مستقل ضمن المؤسسة ويضيف AuditLog، لكنه لا يتحقق في هذا الموضع من توقيع clause-bound.
- Draft PR22 `mcias/reference_points.py:approve`: مراجعة مستقلة وWrittenAuthorization وسجل تدقيق؛ لكنه يعتمد تفويضًا عامًا غير مربوط تشفيريًا بالبند، ويمنع اعتماد الإنتاج صراحةً حتى توفر توقيع مؤسسة مرتبط بمحتوى التعديل.

## التمييز الحاسم
`approved_by`، صلاحيات RBAC، زر الموافقة، وAuditLog **إثبات إجراء عمل داخل النظام**، لا تُعد تلقائيًا توقيعًا تشفيريًا قابلاً للتحقق على بيانات رسم. كذلك نجاح Ed25519 بتوقيع بمفتاح اصطناعي لا يثبت سلطة هذا المفتاح داخل المؤسسة، ولا انتهاء التفويض أو الإبطال.

## مسار دمج محدود مستقبلًا
1. باستخدام مصدر G2 الأصلي المثبت، يبنى payload معياري محدد النسخة يربط `organization_id/provider_code/contract_version_id/contract_version/fee_code/unit/unit_price/currency/effective_from/effective_until/clause_document_id/clause_sha256/clause_locator` مع هوية المؤسسة والموقّع والاعتماد، ومعرّف غرض صريح `mcias.additional_fee_clause.v1`.
2. لا تؤخذ مفاتيح الثقة أو الصلاحيات من API؛ إعادة استعمال سجل مفاتيح المؤسسة الخارجي للتحقق Ed25519، مع توسيعه لاحقًا ليحفظ توقيع payload الرسوم ومصدر الوثيقة ورقم الإصدار، بعد موافقة حوكمة مستقلة.
3. التحقق من المفاتيح والفترة والتفويض الفعلي والإبطال وتعارض نسخ البنود ومراجعة بشرية مستقلة وخريطة الثقة بالعقد الأصلي. لا يُستبدل ذلك بمجرد `ReferencePoint.status=approved` أو `WrittenAuthorization.id`.
4. يفشل التكامل إغلاقًا عند غياب أي حقل أو توقيع أو مفتاح موثوق أو انتهاء/سحب الاعتماد؛ يظل `NOT_VERIFIED / NOT_AUTHORIZED`. لا تستدعي مطابقة A1 البنيوية أي مكوّن منح مالي، ولا تغيّر G3/G5 دون مشروع حوكمة جديد.

## اختبارات اصطناعية
`tests/test_a1_fee_signature_boundary.py` يفحص بدائية Ed25519 الحالية على payload اصطناعي، ويتحقق من فشل التوقيع المفقود/تغيير الإصدار أو بصمة المصدر، ومن بقاء المطابقة البنيوية بلا تصريح قبل وبعد انتهاء السريان. **لا يوجد تنفيذ مصدر توقيع رسوم موثوق بعد.**
