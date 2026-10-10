# دليل تجهيز البيئة الخارجية والتشغيل

معرّف الوثيقة: `MCIAS-DEP-001` · الإصدار: 1.0 · الحالة: مسودة للمراجعة · اللغة: العربية

[English version](DEPLOYMENT_GUIDE_EN.md) · [فهرس الحزمة](ACCEPTANCE_PACK_INDEX.md)

## النطاق والمتطلبات

دليل تجهيز **بيئة اختبار خارجية معزولة**، وليس إذن تشغيل إنتاجي. main هو المصدر الهندسي الحالي؛ يُثبّت SHA كامل قبل النقل. متطلبات النسخة المختبرة: Linux، Python 3.12 (المشروع يسمح 3.11+)، PostgreSQL 16 وعملاء pg_dump/pg_restore المتوافقون، Node 22+ وChromium/Playwright للاختبارات فقط. تحتاج الجهة مساحة تخزين وحملًا وتزامنًا وRPO/RTO معتمدين؛ لا نفرض أرقام سعة تخمينية.

مسؤوليات: DBA للترحيل والأدوار، مشغّل للحساب المحدود، مسؤول أمن للشهادات والمفاتيح والماسح، ومراجع مستقل للأدلة. لا تُستخدم كلمات مرور `.env.example` ولا مفاتيح CI في التشغيل.

## 1. تثبيت النسخة والتحقق من النقل

```bash
git clone https://github.com/overurdream-collab/test2.git
cd test2
# MCIAS_RELEASE_COMMIT: full independently reviewed SHA, supplied out of band.
git checkout --detach "$MCIAS_RELEASE_COMMIT"
git rev-parse HEAD
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test,browser]'
npm ci --ignore-scripts
python -m playwright install --with-deps chromium
```

في النقل دون إنترنت، تحقق من `HANDOFF.json` و`SHA256SUMS` مقابل نسخة موثوقة بقناة مستقلة، ثم ثبّت wheelhouse في venv جديد. البصمة ليست توقيع قبول. أرشيف المصدر مطلوب لأن wheel وحده لا يحوي الترحيلات والاختبارات وأدوات التشغيل. لا تنقل `.env`، أو `deploy/private`، أو `.e2e-output`، أو مصادر ومفاتيح الجهاز السابق.

```bash
# Verified candidate/wheels from an institution-controlled handoff.
python -m pip install --no-index --find-links candidate/wheels mcias
python -m pip check
# Full committed source is still required for Alembic, tests and operator scripts.
```

## 2. فصل قواعد البيانات والأدوار

- قاعدة جديدة للانحدار، وقاعدة أخرى `_e2e` للمتصفح، وقاعدة مستقلة للاستعادة؛ لا تُشغّل pytest على بيانات الجهة.
- حساب ترحيل/مالك إداري منفصل عن المستخدم التشغيلي. التشغيل لا يملك الجداول، ولا rolsuper/CREATEDB/CREATEROLE/REPLICATION/BYPASSRLS أو CREATE في public أو UPDATE/DELETE على audit_log.
- DBA يراجع الصلاحيات الفعلية لكل جدول ومسار؛ عدادات API تحتاج SELECT/INSERT/UPDATE/DELETE على `api_rate_limit_buckets`، مع SELECT على `alembic_version`. لا توجد RLS عامة؛ عزل المؤسسة يعتمد على حراس API وبعض قيود قاعدة البيانات، فلا تُمنح اتصالات SQL للمستخدم النهائي.
- لا ينشئ النشر مستخدم Super Admin أو صلاحيات مؤسسية تلقائيًا. تهيئة الهوية وMFA عبر إجراء محلي معتمد؛ `python -m mcias.bootstrap_mfa --username USERNAME` يطبع سر TOTP مرة واحدة ويُستخدم في طرفية خاصة دون تسجيلها.

## 3. الإعداد المحلي وحيازة الأسرار

تُحمّل المتغيرات من خدمة إدارة أسرار أو جلسة مؤسسية محمية؛ السكربت لا يقرأ ولا ينفّذ `.env`. لا تنسخ values إلى التقرير ولا تستعمل `set -x` أو dumps للبيئة.

| Variable | Use |
|---|---|
| `MCIAS_DATABASE_URL` | Intended runtime PostgreSQL+psycopg identity; secret, not a command-line argument |
| `MCIAS_TEST_DATABASE_URL` | Fresh administrative synthetic regression DB; never production |
| `MCIAS_E2E_DATABASE_URL` | Separate browser/Seed DB ending `_e2e` |
| `MCIAS_ENVIRONMENT` | `development` for synthetic tests; `production` for production-profile checks only |
| `MCIAS_RELEASE_COMMIT` | Exact reviewed 40-character SHA |
| `MCIAS_STORAGE_DIR`, `MCIAS_STORAGE_KEY` | Local private encrypted-source directory, 32-byte hex key |
| `MCIAS_MFA_ENCRYPTION_KEY` | Independently held nonzero 32-byte hex key |
| `MCIAS_AUTHORIZATION_REGISTRY` | Protected, locally provisioned institution-head trust registry |
| `MCIAS_G5_POLICY_VERIFICATION_KEY` | Separate local G5 HMAC verification secret; never a browser setting |
| `MCIAS_TLS_CERT_PATH`, `MCIAS_TLS_HOST` | Exact-host SAN certificate used by preflight |
| `MCIAS_MALWARE_SCAN`, `MCIAS_CLAMAV_HOST`, `MCIAS_CLAMAV_PORT` | Production requires `clamav`, loopback scanner, approved port |
| `MCIAS_RETENTION_ARCHIVE_DIR`, `MCIAS_RETENTION_ENCRYPTION_KEY` | Optional local archival worker directory/key; no purge |
| `MCIAS_ENABLE_UI_DEMO` | Explicit development preview only; disabled for production-profile checks |
| `MCIAS_BOOTSTRAP_TOKEN` | Development-only bootstrap; absent in production |

يُنشأ مخزن الملفات مسبقًا بصلاحيات 0700 ومالك حساب التشغيل، والملفات الخاصة 0600/أقل إذن ممكن. لا يحاول deploy_check كتابة ملف اختبار أو تغيير chmod. تحفظ نسخ احتياطية للمفاتيح منفصلة عن البيانات مع استعادة مزدوجة الاعتماد. لا توجد مفاتيح في المتصفح.

## 4. الترحيل والتشغيل

```bash
# Administrative migration session, separate from runtime credentials.
alembic upgrade head
alembic current
# Switch to runtime identity/environment before starting the API.
python -m uvicorn mcias.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

الرأس الحالي `0018_claim_query_indexes`. بعد الترحيل يبدّل المشغّل إلى حساب التشغيل المحدود؛ لا تعمل الخدمة بحساب DBA. الواجهتان `/admin/dashboard` و`/institution/dashboard` تعيدان حالة الدخول دون سجلات قبل المصادقة. افتح المنفذ عبر وكيل مؤسسي HTTPS فقط عند اعتماده، واضبط proxy trust على عناوين موثوقة محددة لا `*`. API لا يقرأ X-Forwarded-For مباشرة.

`deploy/compose.g9.yml` بديل هندسي اختياري: PostgreSQL داخلي، API غير root، وTLS على `127.0.0.1:8443` فقط. جهّز `deploy/private/{runtime.env,postgres-owner.env,authorization-registry.json,tls.crt,tls.key,encrypted-sources/}` خارج Git، ثم `docker compose -f deploy/compose.g9.yml up -d --build` بعد مراجعة الشبكة والصلاحيات. الصور tags متغيرة والبناء يتصل لتنزيل مكتبات؛ ثبّت digests وwheelhouse معتمدًا قبل الإفراج الإنتاجي.

Compose لا يجهز ClamAV. المحرك يقبل ماسح loopback فقط، لذلك يجب أن يكون الماسح في نفس مساحة شبكة API/المضيف وفق تصميم معتمد، لا حاوية أخرى باسم شبكة غير مسموح. الإنتاج يرفض رفع الملفات عند غياب الماسح؛ لا تُعطّله لتجاوز الفشل.

## 5. فحص التشغيل وتفسير النتيجة

```bash
# Run from the reviewed source checkout with an active runtime environment.
umask 077
./scripts/deploy_check.sh --profile test \
  --url http://127.0.0.1:8000 --expected-commit "$MCIAS_RELEASE_COMMIT" \
  > /secure/operator-evidence/deploy-check.json
# For an institution-hosted, configured production-profile test:
./scripts/deploy_check.sh --profile production \
  --url https://mcias.test.institution.example \
  --expected-commit "$MCIAS_RELEASE_COMMIT" --ca-file /secure/institution-ca.crt
```

السكربت .sh يشغّل deploy_check.py باستخدام python3 أو `MCIAS_CHECK_PYTHON` المحدد. GET محصور في health وصفحة login ووثائق API العامة للتحقق من إغلاقها في production؛ لا يسجل الدخول ولا يرفع ملفًا ولا يرحّل أو يزرع أو يغير سياسة أو يفحص API طبية. SQL SELECT فقط عبر preflight الحالي في جلسة قراءة فقط ومهلة خمس ثوان لكل استعلام تتجاوز خيارات المتصل، وClamAV PING محلي دون إرسال مستند. المهلات محدودة، redirects مرفوضة، TLS يُتحقق منه ولا يوجد خيار insecure، ويُرفض userinfo/query/path في origin.

`0`: جميع الفحوص الهندسية المطلوبة PASS؛ لا يعني قبولًا مؤسسيًا. `2`: BLOCKED، بما فيه `--skip-database` أو غياب هوية Git لأرشيف يحتاج تحققًا مستقلًا. أخطاء الاستخدام يرجعها argparse بـ2. ملفات JSON لا تحتوي URLs كاملة أو أسرارًا أو أجسام أخطاء HTTP. الفحص من داخل سياق خدمة التشغيل؛ حساب غير قادر على الوصول الصحيح يُحجب. لا يثبت الفحص تدوير المفاتيح أو سلطة سجل الثقة أو جودة فحص malware أو backup/restore أو firewall أو SLA.

## 6. التشغيل اليومي والرجوع

عامل `python scripts/retention_worker.py` اختياري بمجدول محلي وحساب محدود؛ يتحقق من أرشيف شهر مكتمل ولا يحذف السجل. تنظيف عدادات الطلبات فقط `--cleanup-rate-buckets`. الأرشيف ليس نسخة قاعدة كاملة ولا يشمل سجلات null actor؛ حدود الحجم موثقة في RETENTION_POLICY.

قبل الترقية: ثبت النسخة وبصمات المصدر، انسخ DB ومخزن الملفات المشفر والمفاتيح بإجراء منفصل، واختبر الاستعادة في قاعدة جديدة. عدة ترحيلات append-only لا تدعم downgrade؛ لا يُنفذ `alembic downgrade` كخطة رجوع عامة. يُستعاد snapshot كامل مع نسخة التطبيق المطابقة بعد قرار المسؤول. ينفذ الفريق [خطة الاختبارات الخارجية](EXTERNAL_TEST_PLAN.md)، ثم UAT واختبار اختراق مستقل؛ لا تُدخل البيانات الحقيقية أو تفعّل سياسة مالية لمجرد نجاح هذا الدليل.
