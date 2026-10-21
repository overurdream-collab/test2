# Shared Audit — عقد النتائج الرسمي v2

المالك: المشرف، بتنسيق صريح مع G5. خط الأساس PR34 `a0f5ed864dad35a415e7173aea82c1b0441b07d8`.

أضيف `audit_state_schema_version=2` إلى عقد الحدث القائم، بالقيم الرسمية MATCH_VERIFIED وVIOLATION_PROVEN وUNRESOLVED وAUDIT_UNAVAILABLE وأسباب مغلقة. تُقرأ الأحداث التاريخية بإصدارها الأول دون تعديلها. دالة `claim_reference_projection` مشتركة بين المنتج والكاتب، وتحتفظ بمعرفات المصدر والصف والمستند والنسخة والاعتماد دون قيم المستفيد أو نص المستند.

الكاتب يتحقق من تطابق النتيجة والإصدار والسبب مع AuditSnapshot المحفوظ، ومن الست شهادات المعتمدة والمكتملة والسارية مع تنفيذ جميع الفحوص قبل حفظ نتيجة مكتملة. للمخالفة يلزم إثبات قاعدة في findings. يستمر منع تكرار الحدث بمفتاح السجل المشترك نفسه، والـCommit والـRollback بملكية المستدعي.

التحقق الفعلي: **35 passed، صفر skipped، 36.77s** على SQLite وPostgreSQL16.15 الاصطناعية. أمر التنفيذ:

```sh
PYTHONPATH=. MCIAS_INPUTS_AUDIT_DATABASE_URL=postgresql+psycopg://postgres:synthetic-only@127.0.0.1:55432/mcias_inputs_audit MCIAS_INPUTS_AUDIT_ALLOW=YES /workspace/security-venv/bin/python -m pytest -q tests/test_shared_audit_contract_v2.py tests/test_shared_audit_inputs_pg16.py tests/test_operational_controls.py
```

تشمل الاختبارات النتائج الأربع بعد Commit وإعادة القراءة، والتوافق التاريخي، ورفض تبديل النسخة أو الحالة/السبب غير المتوافق، ومنع اكتمال النتيجة بمرجع ناقص، ومنع PHI، وتزامن إعادة المحاولة والعزل والـRollback. استُخدمت شهادات fixture في اختبارات عقد الكاتب فقط؛ إثبات سلطة بيانات G3 الأصلية من اختصاص اختبار المسار التكاملي، ولا يُستنتج من هذه fixtures. انحدار HTTP429 اجتاز مع بقاء حد الخدمة كما هو.

CI لهذا التعديل لم يُشغّل بعد؛ لا يُنسب نجاح PR34 السابق لهذا التعديل. الخطوة التالية: تركيب Commit مع G3/G5 واختبار native PG16 ثم تحديث PR القائم دون Merge أو Deployment.
