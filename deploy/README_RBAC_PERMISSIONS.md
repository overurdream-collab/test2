# RBAC Runtime Permissions

## الغرض

منح حساب التشغيل صلاحية UPDATE على أعمدة الإغلاق لجداول RBAC، وعلى
`organizations.name` لدعم قفل الجهة أثناء تهيئة الصلاحيات. الحساب الافتراضي
هو `laptop_runtime`، ويمكن اختيار اسم مختلف دون تعديل SQL أو Migration.

## متى يُشغّل

بعد ترقية المخطط إلى `0022_rbac_authority` أو إصدار لاحق، وإنشاء حساب التشغيل ومنحه
صلاحيات SELECT وINSERT اللازمة. يكفي تطبيقه مرة واحدة لكل قاعدة وحساب؛ يمكن
إعادة تشغيله بأمان. يجب إعادة تطبيقه إذا أُعيد إنشاء القاعدة أو الحساب.

شغّله بحساب إعداد يملك الجداول أو حق منح هذه الصلاحيات، مثل `laptop_owner`
في إعداد اللابتوب، وليس بحساب التشغيل الذي سيستقبل المنح.

## كيف يُشغّل

يتطلب Bash وعميل PostgreSQL `psql` إصدار 10 أو أحدث؛ PostgreSQL 16 هو خط
اختبار المشروع. على Windows استخدم بيئة Bash يتوفر فيها `psql`، مثل WSL.

من جذر المستودع، وببيانات اتصال الإعداد المحلية:

```bash
export MCIAS_DATABASE_URL='postgresql://<setup_user>:<password>@<host>:<port>/<database>'
export MCIAS_RUNTIME_USER='laptop_runtime'
bash deploy/setup_rbac_permissions.sh
```

`MCIAS_DATABASE_URL` مطلوب. `MCIAS_RUNTIME_USER` اختياري وافتراضيه
`laptop_runtime`. تُقبل عناوين `postgresql://` و`postgres://`، ويحوّل الغلاف
بادئة SQLAlchemy `postgresql+psycopg://` إلى الصيغة التي يفهمها `psql`.
رمّز المحارف الخاصة في بيانات اتصال URI. لا تحفظ كلمة المرور في المستودع.

## ماذا يفعل

يتحقق SQL من وجود الحساب، ثم يطبّق المنح الستة ضمن معاملة واحدة. إذا لم يوجد
الحساب، يطبع WARNING ويخرج بنجاح دون تطبيق أي GRANT؛ أنشئ الحساب وأعد التشغيل.
أخطاء الاتصال أو المخطط أو صلاحية المنح تُرجع خروجاً غير صفري. فشل أي GRANT
يلغي جميع المنح في تلك المحاولة. يُقتبس اسم الحساب بأمان عبر متغيرات `psql`.

| الجدول | الأعمدة الممنوح تحديثها |
|---|---|
| `public.users` | `status`, `effective_to`, `closed_by`, `closed_at`, `close_reason`, `active` |
| `public.groups` | `status`, `effective_to`, `closed_by`, `closed_at`, `close_reason` |
| `public.group_permissions` | `status`, `effective_to`, `closed_by`, `closed_at`, `close_reason` |
| `public.user_groups` | `status`, `effective_to`, `closed_by`, `closed_at`, `close_reason` |
| `public.user_permissions` | `status`, `effective_to`, `closed_by`, `closed_at`, `close_reason` |
| `public.organizations` | `name` |

## حدود المنح والحماية

`SELECT FOR UPDATE` يحتاج UPDATE على عمود واحد على الأقل في الجدول المقفول.
منح `organizations.name` يدعم القفل، ويسمح فعلياً بتغيير اسم الجهة أيضاً؛
لا توجد هنا صلاحية للقفل وحده. لم يُمنح UPDATE على المفتاح الأساسي `id`.

Triggers الحالية `mcias_check_close` و`mcias_prevent_delete` تحمي السجلات
المغلقة وتمنع الحذف في الجداول المرتبطة بها. لا تمنع كل تعديل على السجلات
المفتوحة، ولا تحمي `organizations.name`. التفويض وعزل الجهة يبقيان مسؤولية
الخدمات وAPI الحالية؛ الحساب التشغيلي ليس حساب مستخدم بشري مباشر.

السكربت يضيف المنح فقط؛ لا يسحب صلاحيات أوسع موجودة أو موروثة من أدوار أخرى.
لا يمنح DELETE أو UPDATE لسجل `audit_log`، ولا يغيّر الجداول أو Triggers.

## التحقق

```bash
pytest tests/ -v
```

الاختبارات الحالية تستخدم حساب PostgreSQL اختبارياً؛ نجاحها لا يثبت نجاح
`laptop_runtime`. للتحقق من حساب التشغيل، طبّق السكربت في قاعدة اختبار معزولة
واختبر الإنشاء والإغلاق والسحب وإزالة العضوية والتحويل وتهيئة الصلاحيات،
وتحقق من رفض تحديث الأعمدة غير الممنوحة ومنع الحذف وتعديل سجل التدقيق.

تُمنح SELECT وINSERT على `rbac_provisionings` و`rbac_grant_origins` دون UPDATE أو DELETE. راجع [خطة التوحيد](../docs/RBAC_UNIFICATION.md) قبل تفعيل أي منح قديم.
