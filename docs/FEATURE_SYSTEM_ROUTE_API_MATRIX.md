# مصفوفة المسارات وAPI — نظام الميزات

أضيف 20 تعريف endpoint و35 تعريف route. إجمالي routes.json =94. مسارات السجلات الديناميكية تعريفات قوالب وليست سجلات مصطنعة.

## API الجديدة

| # | الطريقة | المسار | الوظيفة/الحماية |
|---|---|---|---|
| 1 | GET | `/api/v1/admin/features` | كتالوج؛ Super Admin + MFA |
| 2 | GET | `/api/v1/admin/features/tree` | شجرة؛ Super Admin + MFA |
| 3 | GET | `/api/v1/admin/feature-organizations` | الجهات بترقيم؛ Super Admin + MFA |
| 4 | GET | `/api/v1/organizations/{org_id}/features` | استحقاقات؛ الجهة نفسها أو Super Admin |
| 5 | POST | `/api/v1/organizations/{org_id}/features/{code}/grant` | منح ورقة؛ Super Admin + MFA |
| 6 | POST | `/api/v1/organizations/{org_id}/features/{code}/revoke` | سحب مؤرخ مع سبب؛ Super Admin + MFA |
| 7 | PUT | `/api/v1/organizations/{org_id}/features` | فروق ذرية وإصدار متوقع؛ Super Admin + MFA |
| 8 | GET | `/api/v1/me/features` | سياق جلسة وميزات ∩ صلاحيات |
| 9 | GET | `/api/v1/feature-data/catalog/{kind}` | كتالوج؛ Super Admin + MFA |
| 10 | GET | `/api/v1/registry/{feature}/schema` | حقول وصلاحيات المدخلات؛ استحقاق + RBAC + الجهة الحالية |
| 11 | GET | `/api/v1/registry/{feature}/records` | قائمة وبحث وتصفية وترقيم؛ استحقاق + RBAC + الجهة الحالية |
| 12 | POST | `/api/v1/registry/{feature}/records` | إضافة مشفرة غير معتمدة مالياً؛ استحقاق + RBAC + الجهة الحالية |
| 13 | GET | `/api/v1/registry/{feature}/records/{record_id}` | تفاصيل سجل مسموح؛ استحقاق + RBAC + الجهة الحالية |
| 14 | GET | `/api/v1/registry/{feature}/records/{record_id}/history` | تاريخ نسخ غير قابل للتعديل؛ استحقاق + RBAC + الجهة الحالية |
| 15 | POST | `/api/v1/registry/{feature}/records/{record_id}/close` | حدث إغلاق مؤرخ بسبب ونسخة متوقعة؛ استحقاق + RBAC + الجهة الحالية |
| 16 | POST | `/api/v1/registry/{feature}/records/{record_id}/versions` | نسخة جديدة لسجل مغلق؛ استحقاق + RBAC + الجهة الحالية |
| 17 | POST | `/api/v1/registry/{feature}/imports` | رفع أصلي CSV/XLSX/PDF؛ ingestion.upload؛ استحقاق + RBAC + الجهة الحالية |
| 18 | GET | `/api/v1/registry/{feature}/imports/{document_id}/preview` | معاينة واستخراج أو حجر؛ استحقاق + RBAC + الجهة الحالية |
| 19 | POST | `/api/v1/registry/{feature}/imports/{document_id}/commit` | تأكيد بشري وحفظ ذري؛ استحقاق + RBAC + الجهة الحالية |
| 20 | GET | `/api/v1/registry/{feature}/records/{record_id}/evidence/{document_id}` | تنزيل مصدر مرتبط بجهة السجل؛ استحقاق + RBAC + الجهة الحالية |

## جميع المسارات الجديدة

| # | المسار | العنوان | الميزة | API/الحالة |
|---|---|---|---|---|
| 1 | `/admin/features` | ميزات الجهات | `حوكمة مركزية` | API الميزات والإدارة؛ حفظ ذري فعلي |
| 2 | `/admin/organizations/:id/features` | ميزات الجهة | `حوكمة مركزية` | API الميزات والإدارة؛ حفظ ذري فعلي |
| 3 | `/institution/inputs/contracts` | العقود | `inputs.contracts` | `/api/v1/registry/inputs.contracts`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 4 | `/institution/inputs/regulations` | الآليات واللوائح | `inputs.regulations` | `/api/v1/registry/inputs.regulations`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 5 | `/institution/inputs/exceptions` | الاستثناءات | `inputs.exceptions` | `/api/v1/registry/inputs.exceptions`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 6 | `/institution/inputs/approvals` | الموافقات والتفويضات | `inputs.approvals` | `/api/v1/registry/inputs.approvals`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 7 | `/institution/inputs/caps` | السقوف | `inputs.caps` | `/api/v1/registry/inputs.caps`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 8 | `/institution/inputs/coverage` | التغطية | `inputs.coverage` | `/api/v1/registry/inputs.coverage`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 9 | `/institution/beneficiaries/names` | أسماء المستفيدين | `beneficiaries.names` | `/api/v1/registry/beneficiaries.names`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 10 | `/institution/beneficiaries/categories` | فئات المستفيدين | `beneficiaries.categories` | `/api/v1/registry/beneficiaries.categories`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 11 | `/institution/beneficiaries/cost-sharing` | المشاركة في التكلفة | `beneficiaries.cost_sharing` | `/api/v1/registry/beneficiaries.cost_sharing`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 12 | `/institution/providers/hospitals` | المستشفيات | `providers.hospitals` | `/api/v1/registry/providers.hospitals`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 13 | `/institution/providers/clinics` | العيادات | `providers.clinics` | `/api/v1/registry/providers.clinics`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 14 | `/institution/providers/labs` | المختبرات | `providers.labs` | `/api/v1/registry/providers.labs`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 15 | `/institution/providers/radiology` | الأشعة | `providers.radiology` | `/api/v1/registry/providers.radiology`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 16 | `/institution/providers/pharmacies` | الصيدليات | `providers.pharmacies` | `/api/v1/registry/providers.pharmacies`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 17 | `/institution/providers/services` | الخدمات | `providers.services` | `/api/v1/registry/providers.services`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 18 | `/institution/providers/prices` | التسعيرات | `providers.prices` | `/api/v1/registry/providers.prices`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 19 | `/admin/inputs/contracts` | العقود | `inputs.contracts` | `/api/v1/registry/inputs.contracts`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 20 | `/admin/inputs/regulations` | الآليات واللوائح | `inputs.regulations` | `/api/v1/registry/inputs.regulations`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 21 | `/admin/inputs/exceptions` | الاستثناءات | `inputs.exceptions` | `/api/v1/registry/inputs.exceptions`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 22 | `/admin/inputs/approvals` | الموافقات والتفويضات | `inputs.approvals` | `/api/v1/registry/inputs.approvals`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 23 | `/admin/inputs/caps` | السقوف | `inputs.caps` | `/api/v1/registry/inputs.caps`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 24 | `/admin/inputs/coverage` | التغطية | `inputs.coverage` | `/api/v1/registry/inputs.coverage`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 25 | `/admin/beneficiaries/names` | أسماء المستفيدين | `beneficiaries.names` | `/api/v1/registry/beneficiaries.names`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 26 | `/admin/beneficiaries/categories` | فئات المستفيدين | `beneficiaries.categories` | `/api/v1/registry/beneficiaries.categories`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 27 | `/admin/beneficiaries/cost-sharing` | المشاركة في التكلفة | `beneficiaries.cost_sharing` | `/api/v1/registry/beneficiaries.cost_sharing`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 28 | `/admin/providers/hospitals` | المستشفيات | `providers.hospitals` | `/api/v1/registry/providers.hospitals`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 29 | `/admin/providers/clinics` | العيادات | `providers.clinics` | `/api/v1/registry/providers.clinics`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 30 | `/admin/providers/labs` | المختبرات | `providers.labs` | `/api/v1/registry/providers.labs`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 31 | `/admin/providers/radiology` | الأشعة | `providers.radiology` | `/api/v1/registry/providers.radiology`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 32 | `/admin/providers/pharmacies` | الصيدليات | `providers.pharmacies` | `/api/v1/registry/providers.pharmacies`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 33 | `/admin/providers/services` | الخدمات | `providers.services` | `/api/v1/registry/providers.services`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 34 | `/admin/providers/prices` | التسعيرات | `providers.prices` | `/api/v1/registry/providers.prices`؛ إدخال مقترح مؤرخ؛ ليس تفعيل G3/G5 |
| 35 | `/institution/users` | مستخدمو الجهة | `users.list` | `/api/v1/feature-data/catalog/users`؛ قراءة فقط |

## الأقسام والربط بالبيانات المرجعية

| القسم | الأوراق | تنفيذ API | اتصال G3/G5 المالي |
|---|---|---|---|
| المدخلات | 6 | سجل مشفر + إضافة/إغلاق/نسخ/معاينة/استيراد/دليل | لا تفعيل تلقائي؛ اعتماد منفصل مطلوب |
| المستفيدون | 3 | أسماء خاصة وفئات ومشاركة تكلفة، مشفرة ومؤرخة | لا تحويل تلقائي إلى Enrollment مؤهل مالياً |
| مقدمو الخدمة | 7 | 5 أنواع مقدمين + خدمات + أسعار | لا تفعيل تلقائي للعقود أو التعريفات |

الحاويات تظهر عند وجود ورقة مسموحة؛ منحها لا يمنح أوراقاً. الميزات الأخرى في الكتالوج لا تعني أن كل تحليل مالي أو صفحة قديمة أصبح عاملاً. معلومات السجلات ودليلها تُقرأ فقط ضمن جهة الفاعل؛ Super Admin لا يتجاوز هذا الشرط.
