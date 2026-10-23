# توحيد RBAC وفصل الإدارة التقنية عن الاعتماد المالي

## النطاق والمصدر المعتمد

المصدر الوظيفي الوحيد هو `GroupPermission → Group → UserGroup` بعد مراجعة الجهة وتوثيق أصل المنح. جميع نقاط التفويض القديمة والجديدة تستخدم `authorization_service.check_permission_unified`، عبر محوّل `policy.has_permission` أو الاعتماد المركزي في API. لا يوجد جمع أو رجوع تلقائي إلى `RolePermission` أو `UserPermission`.

تُحفظ جداول الأدوار والمنح الفردية السابقة. وجود سجل قديم لا يمنح وصولًا. يبقى `UserRole(super_admin)` علامة هوية للإدارة التقنية مع MFA، وليس مصدرًا للاعتماد المالي. الحقل `is_super_admin` وحده لا يمنح صلاحيات الإدارة التقنية.

| النوع | العمليات |
|---|---|
| Super Admin + MFA | إنشاء فئات فارغة، إعداد الكتالوج، معاينة/تطبيق خطة معتمدة من الجهة، سحب المنح وإغلاق الفئات، إدارة الميزات |
| Institution Admin | إنشاء وإغلاق حسابات الموظفين، إسناد فئات وافقت عليها الجهة، إزالة العضويات ونقلها ذريًا |
| موظف وظيفي | صلاحيات فئته المعتمدة والسارية، ضمن الجهة نفسها |
| حساب تقني | لا يستطيع الاعتماد المالي أو تفعيل السياسة المالية حتى عند وجود منح وظيفي يحمل تلك الصلاحية |

لا يستطيع مدير الجهة إنشاء الفئات أو تعديل صلاحياتها، أو إسناد فئة إلى نفسه. قد يملك الحساب التقني صلاحيات تشغيل/قراءة وظيفية **ممنوحة صراحة في خطة مستقلة معتمدة**؛ لا يكتسبها من هويته التقنية. تُرفض صلاحيات الاعتماد المالي للحساب التقني دائمًا. الاعتماد المالي الحالي G5/G6 وتوقيعاته وفصل الأطراف تبقى ضوابط مستقلة.

## Migration 0022_rbac_authority

السابق: `0021_organization_features`. لا تعديل للترحيلات 0019 أو 0021.

- `groups.management_scope`: `functional` أو `institution_admin`؛ يُصنّف قالب `admin` المفتوح إداريًا دون تفعيله.
- `rbac_provisionings`: خطة الجهة، المطبق، المعتمد المستقل، مرجع الاعتماد، التوقيع والبصمة.
- `rbac_grant_origins`: رابط كل منح/عضوية بأصله ومراجعة الجهة.
- حماية التاريخ من UPDATE/DELETE، ومنع تغيير هوية المنح، والتحقق من اتساق الجهة في سجل الأصل.
- الترحيل الهيكلي **لا ينقل أو يفعّل منحًا تلقائيًا**.
- يسمح downgrade على قاعدة لم تُنشأ فيها مراجعات RBAC؛ يُرفض بعد إنشاء التاريخ المعتمد لمنع محوه. الاسترجاع حينئذٍ يتم من نسخة احتياطية مراجعة مع نسخة التطبيق المتوافقة.

الأسماء التاريخية والأكواد الفعلية لا تُترجم إلى صلاحيات أوسع تلقائيًا. في المنح القديمة بلا تواريخ (UserRole/RolePermission)، تاريخ تفعيل المنح الجديد هو يوم تطبيق المراجعة، مع حفظ معرفات السجل الأصلي؛ لا تُختلق تواريخ قديمة. المنح المؤرخة تُحفظ فتراتها. تُستبعد المنح المغلقة من التفعيل وتبقى في جداول التاريخ.

## تشغيل مؤسسي مضبوط

1. خذ نسخة احتياطية واختبر الاسترجاع على قاعدة معزولة. أوقف العمليات الحساسة خلال الانتقال؛ بعد تحديث المصدر تُرفض المنح غير المراجعة.
2. راجع حساب Super Admin الفعلي وتسجيل MFA. حدد ممثل الجهة المفوض، مختلفًا عن المطبق التقني.
3. جهز سجل مفاتيح **عامة** معتمدًا خارج التطبيق، وحدد `MCIAS_RBAC_TRUST_REGISTRY` في خدمة API. لا تُرسل مفتاحًا خاصًا أو عامًا في طلب الاعتماد.

```json
{"trusted_approvers":{"ORGANIZATION_ID":{"INSTITUTION_APPROVER_USER_ID":"ED25519_PUBLIC_KEY_HEX"}}}
```

يجب أن يقرأه حساب التشغيل دون القدرة على تعديل الملف أو المجلد الأب، وأن يُثبت عبر mount للقراءة فقط في الإنتاج. تُرفض الروابط الرمزية والملفات القابلة للكتابة للمجموعة/الجميع. إعداد السجل خارج التطبيق هو حد الثقة؛ SQL history وحده ليس موافقة مؤسسية.

4. شغّل `alembic upgrade head` بحساب مالك الترحيل. طبق `deploy/setup_rbac_permissions.sh` بحساب مخول، مع `MCIAS_DATABASE_URL` و`MCIAS_RUNTIME_USER` الصحيحين. لا تمنح UPDATE/DELETE عامين لتاريخ RBAC أو سجل التدقيق.
5. سجل الدخول بحساب تقني وMFA، وافتح `/admin/rbac-migration` أو اطلب `GET /api/v1/admin/rbac/migration-preview`.
6. راجع كل فئة ومنح وعضوية واستبعاد مع الجهة. يجوز تقليص خطة الترحيل بحذف مجموعات أو منح أو عضويات؛ لا يجوز تغيير هوية المصدر أو إضافة منح غير موجود. تُعدّل المنح الجديدة عبر خطة إعداد مستقلة.
7. يوقع ممثل الجهة المستقل المحتوى التالي باستخدام Ed25519 وبالمفتاح الخاص المحتفظ به خارج MCIAS:

```json
{"purpose":"mcias-rbac-v1","manifest":{},"approved_by":"INSTITUTION_APPROVER_USER_ID","approval_reference":"SIGNED_INSTITUTION_REFERENCE"}
```

قبل التوقيع، تسلسل JSON هو UTF-8، مفاتيح مرتبة، بدون مسافات بين العناصر، `ensure_ascii=false`، `allow_nan=false`. التوقيع hex على البايتات نفسها، وليس على النص المعروض بصيغة pretty-print. `manifest` هو الخطة المراجعة كاملة. تمثل بصمة SHA-256 هذا المستند الموقّع.

8. يرفع Super Admin الملف المعتمد إلى الشاشة أو `POST /api/v1/admin/rbac/apply`:

```json
{"manifest":{},"approved_by":"INSTITUTION_APPROVER_USER_ID","approval_reference":"SIGNED_INSTITUTION_REFERENCE","signature":"ED25519_SIGNATURE_HEX"}
```

الفاعل من الجلسة وليس من الطلب. يُرفض التوقيع غير المعتمد، أو المعتمد غير المستقل/غير الساري/خارج الجهة، أو تغير المصدر بعد المعاينة. تُنفذ الخطة وتاريخها في معاملة واحدة؛ إعادة الخطة نفسها لا تكرر المنح. لا تُستخدم قيود UNIQUE لإخفاء خطأ ثم الاستمرار في جلسة معطوبة.

9. تحقق من `GET /api/v1/admin/rbac/history`، و`/api/v1/permissions/me`، و`/api/v1/workspace/context`، ومن حالات 401/403 وفصل الواجبات فعليًا. لا تُعد فتح منحًا مغلقًا لإعادته؛ اعتمد منحًا جديدًا.

## إعداد الفئات بعد الانتقال

`POST /api/v1/admin/rbac/configuration-preview` يستقبل `group_id` و`permission_ids` و`membership_user_ids` الاختياري. تستخدم العضويات الموقعة لتعيين مدير الجهة الأول أو التعيينات التي اعتمدتها الجهة صراحة، وليس لتجاوز الفصل بين الإدارة التقنية والاعتماد المالي. يتطلب إضافة أو تغيير مجموعة المنح مراجعة الجهة والتوقيع المستقل نفسه. يحفظ التطبيق المنح السابقة المغلقة، وينشئ منحًا جديدًا عند الحاجة. السحب الأمني المباشر لا يحتاج صلاحية اعتماد مالي.

مسار المنح الفردي القديم يرفض الإنشاء؛ السحب من سجل فردي تاريخي يبقى متاحًا للإدارة التقنية ولا يحذف التاريخ. مسار منح صلاحية للفئة دون خطة موقعّة يرفض العملية. لا تُعاد صلاحية مسحوبة بسبب بقاء UserRole أو UserPermission قديم.

كتالوج RBAC: 94 صلاحية سابقة + الصلاحية القائمة في API أصلًا `profile.read` = 95. إضافة profile إلى الكتالوج لا تمنحها تلقائيًا للمستخدمين. الأكواد التاريخية المراجعة تبقى بأسمائها الأصلية؛ تعرض واجهات الصلاحيات الفعالة ما يمنح فعليًا، لا اتحاد المصادر القديمة.

## اللابتوب والاختبارات الاصطناعية

`mcias.seed.authorization.approve_synthetic` مخصص فقط لوضع development وقاعدة PostgreSQL باسم ينتهي بـ `_e2e`. يصنع توقيع fixture واضحًا ومفاتيح اختبار خاصة خارج المستودع. لا يمثل طلبًا أو توقيعًا من الجهة. لا يستخدمه مسار API أو تهيئة الإنتاج.

Compose اللابتوب يحدد سجل الثقة الاصطناعي داخل state، ويحدّث setup المنح الاصطناعية المراجعة مع حفظ الأصول. تبقى ملفات المفاتيح الاختبارية خاصة، ولا تُنسخ إلى الإنتاج. لا يتغير تعداد المطالبات أو البيانات الطبية أثناء اختبار الترحيل. لم يُشغّل هذا التغيير على قاعدة عميل فعلية.

## English operational summary

The sole functional authorization source is institution-reviewed group grants and memberships. Legacy roles and individual grants remain as historical records and never provide fallback authority. An MFA-enrolled `super_admin` role identifies technical administration; technical identities cannot financially approve policies, claims or governance decisions.

Schema 0022 adds immutable provisioning manifests and grant provenance. It does not activate grants automatically. An independently pinned institutional Ed25519 signer approves the exact migration/configuration plan; the authenticated technical administrator applies it atomically. Stale source snapshots, invalid signatures, tenant mismatches and self-approval are rejected. Repeating an approved plan is idempotent. Production keys are provisioned out of band and the public registry must be read-only to the runtime account.

Institution administrators manage staff and assign approved groups, but cannot configure group permissions or self-assign. Individual functional grants are retired. Historical grants are never deleted. Financial policy authorization, human approval and immutable financial snapshots remain independent controls. Synthetic fixture signatures and passing tests are not institutional production acceptance.

### أقفال المراجعة بالحساب المحدود

تستخدم سجلات حوكمة G6 وتعريفات/نتائج G8 أقفال PostgreSQL استشارية داخل المعاملة، بدل `SELECT FOR UPDATE` الذي يحتاج UPDATE على الجدول المقروء. يُحفظ تسلسل القرارات والتحقق من الفصل بين الأطراف، دون منح حساب التشغيل قدرة تعديل هذه السجلات. لا تتغير الحسابات المالية أو قواعد الاعتماد. المفاتيح مرتبطة بنوع السجل والجهة ومعرّف السجل، وليست SQL مُدخلًا من المستخدم.
