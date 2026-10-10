# نقل النسخة المجمعة إلى بيئة اختبار خارجية

فرع العمل: `feat/mcias-integrated-candidate`، يجمع الواجهات PR #11 مع تقوية
الإصدار G9 في PR #10. الفروع الأصلية لم تُدمج في main. هذه نسخة هندسية للاختبار
ببيانات اصطناعية، وليست إصدارًا إنتاجيًا معتمدًا.

## ما يلزم من البيئة

- Linux، Python 3.12، PostgreSQL 16 وأدواته `pg_dump`/`pg_restore`، Node 22+.
- Chromium مع Playwright، أو تشغيل بيئة CI المرفقة. Docker Compose اختياري.
- حساب إدارة خاص بقاعدة الاختبار لترحيل الجداول وإنشاء أدوار اختبار مؤقتة.
  حساب التطبيق في التشغيل الفعلي يجب أن يكون مستقلًا ومحدود الصلاحيات.
- مصادر/مفاتيح اختبار منفصلة تمامًا عن أي بيانات أو مفاتيح مؤسسية حقيقية.
- قاعدة جديدة للاختبارات الكاملة؛ اسم قاعدة دورة المتصفح ينتهي بـ `_e2e`.
  اختبارات الترحيل/الاستعادة ليست مناسبة لقاعدة مستخدمة أو بيانات حقيقية.

## النقل عبر Git أو أرشيف المصدر

```bash
git clone https://github.com/overurdream-collab/test2.git
cd test2
git checkout feat/mcias-integrated-candidate
git rev-parse HEAD
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test,browser]'
npm ci --ignore-scripts
python -m playwright install --with-deps chromium
```

عند النقل بأرشيف، قارن SHA-256 للأرشيف مع القيمة المسلمة عبر قناة مستقلة، ثم
فكّه في مجلد جديد. يتضمن المصدر ترحيلات Alembic والاختبارات والوثائق؛ حزمة wheel
وحدها لا تحتوي تجهيز المشروع الكامل. لا تنقل `.env` أو `deploy/private` أو
`.e2e-output` أو مستندات المصدر أو مفاتيح الجهاز الحالي.

## الاختبارات الكاملة

استخدم عنوانًا محليًا لقاعدة جديدة عبر متغير محمي، دون لصقه في تقارير عامة:

```bash
export MCIAS_TEST_DATABASE_URL='<fresh dedicated PostgreSQL test URL>'
python -m pytest -q
npm test
npm run check
python -m compileall -q mcias tests scripts
```

يجب أن تنفّذ اختبارات PostgreSQL والاستعادة بالفعل دون تخطي؛ الحساب الإداري
مخصص للاختبار فقط. لا تعاود الاختبارات الكاملة على القاعدة نفسها لأن بعض تجهيزات
الاختبارات الموروثة تستخدم مفاتيح ثابتة. أنشئ قاعدة جديدة عند إعادة التشغيل.

## دورة المتصفح والاستيعاب والمراجعة

أنشئ قاعدة أخرى جديدة ينتهي اسمها بـ `_e2e`. عيّن المتغيرات التالية في بيئة
الاختبار فقط؛ يولّد المثال مفاتيح مؤقتة لا تُستخدم في الإنتاج:

```bash
export MCIAS_ENVIRONMENT=development
export MCIAS_ENABLE_UI_DEMO=true
export MCIAS_E2E_DATABASE_URL='<fresh dedicated PostgreSQL URL ending in _e2e>'
export MCIAS_DATABASE_URL="$MCIAS_E2E_DATABASE_URL"
export MCIAS_STORAGE_DIR="$PWD/.e2e-output/integrated-sources"
export MCIAS_STORAGE_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export MCIAS_MFA_ENCRYPTION_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python scripts/seed_workspace_e2e.py
python -m uvicorn mcias.app:app --host 127.0.0.1 --port 8002 --no-access-log
```

في طرفية ثانية بنفس المتغيرات والمفاتيح:

```bash
python scripts/check_workspace_browser.py --base-url http://127.0.0.1:8002
python scripts/check_workspace_live.py --base-url http://127.0.0.1:8002
python scripts/check_integrated_workflow.py --base-url http://127.0.0.1:8002
```

احفظ ملفات `*results.json` والصور من `.e2e-output` ضمن سجل الاختبار الداخلي.
لا تنشر `live-fixture.json` لأنه يتضمن بيانات دخول اصطناعية. دورة المتصفح الجديدة
تنشئ حسابات اصطناعية مع MFA وتجرب الرفع والحجر والاستيراد والموافقة المستقلة
والاعتراض والتصدير. G5 يستخدم تجهيز لقطة اصطناعية من المحرك، لأن API تشغيله غير
متاح؛ لا تُفسّر هذا الاختبار كإثبات جاهزية تفعيل سياسة مالية إنتاجية.

## التحقق من التغليف والتشغيل الداخلي

```bash
python -m pip wheel . -w dist/wheelhouse
python scripts/g9_release.py build --repo . --wheels dist/wheelhouse \
  --output dist/integrated-candidate --commit <exact reviewed 40-character SHA>
python scripts/g9_release.py verify --directory dist/integrated-candidate
```

بعد تثبيت النسخة المراجعة في Git وتجهيز wheelhouse يمكنك إنشاء حزمة نقل كاملة:

```bash
python scripts/build_integrated_handoff.py --wheelhouse dist/wheelhouse \
  --output dist/external-handoff
cd dist/external-handoff
sha256sum -c SHA256SUMS
```

تتضمن الحزمة `mcias-source.tar.gz` للمصدر والاختبارات والترحيلات، و`candidate`
للـwheelhouse وإيصال G9، و`HANDOFF.json` للـSHA الدقيق والبصمات. يرفض البناء شجرة
عمل غير مثبتة أو مسارات بيانات/مفاتيح خاصة ملتزمًا بها في Git. الحزمة المحلية
المجهزة هنا توافق Linux x86_64 وPython 3.12؛ يلزم بناء تبعيات جديدة لأي هدف مختلف.

يتضمن إيصال G9 بصمات wheel والوثائق وإعدادات النشر. قارن الإيصال بنسخة موثوقة
مستقلة؛ البصمة وحدها ليست توقيعًا أو اعتمادًا. تبعيات wheel يجب أن توافق نظام
ومعمارية الجهاز المنقول إليه؛ التشغيل دون شبكة يحتاج wheelhouse كاملًا ومراجعًا.
Dockerfile الحالي نموذج بناء يعتمد على شبكة وتاجات صور متغيرة.

للتجربة عبر TLS اتبع `G9_RELEASE.md` لتوفير الشهادة والبيئة والمفاتيح خارج Git،
وترحيل القاعدة بهوية الإدارة، ثم إعداد هوية تشغيل محدودة. المنفذ المتاح في Compose
هو `127.0.0.1:8443` فقط. افحص `python -m mcias.preflight_g9 --check-database` على
الجهاز المستهدف بعد تجهيز الضوابط. نجاحه لا يمنح قبولًا إنتاجيًا.

## ترتيب الاعتماد والخطوة بعد النقل

1. نفّذ الاختبارات الآلية أعلاه على SHA نفسه وسجّل بيئة التشغيل والنتائج.
2. نفّذ قائمة `INTEGRATED_UAT_AR.md` مع مستخدمين ممثلين للأدوار.
3. راجع `INTEGRATED_SECURITY_REVIEW.md` وحدود مصفوفة المسارات والـAPI.
4. حدد أحجام البيانات/التزامن/P95/RPO/RTO، ثم اختبر الحمل والاستعادة على الجهاز
   المستهدف؛ قياسات التطوير لا تثبت SLA هناك.
5. استكمل قرارات المؤسسة: الحقول الطبية، الصلاحيات، أولوية العقود، التقريب،
   التوقيعات، الاحتفاظ والمفاتيح. راجع واعتمد الفروع بالترتيب دون تجاوز عقد القبول.

لم يُنفذ نقل أو اختبار على بيئتكم الخارجية بعد؛ الوصول إليها والتشغيل عليها
خطوة لاحقة وفق توجيهكم. جميع بوابات G0–G9 تحتفظ بحالتها غير المعتمدة.
