# Runbook اختبار اللابتوب

معرّف الوثيقة: `MCIAS-LAP-003` · الإصدار: 1.0 · التاريخ: 2026-10-11 · الحالة: تعليمات للتنفيذ بعد الموافقة؛ لم تنفذ على اللابتوب

[English](LAPTOP_RUNBOOK_EN.md) · [الخطة](LAPTOP_TEST_PLAN.md) · [قائمة التحقق](LAPTOP_TEST_CHECKLIST.md) · [التقرير](LAPTOP_TEST_REPORT.md) · [دليل الإعداد المفصل](WINDOWS_LAPTOP_GUIDE.md)

## 1. الموافقة وتثبيت النسخة — LAP-01، LAP-02

سجل موافقة المستخدم على التنفيذ وأفعال التهيئة/الإدخال وإعادة التشغيل في التقرير قبل العمل. التوثيق الحالي لا يمنح هذه الموافقة. اقرأ الخطة وحدود الحزمة، وحدد المشغّل والمراجع. لا ترفع الفرع أو تدمجه أثناء الجولة؛ push إلى هذا الفرع يشغّل CI تلقائياً.

بعد الموافقة، افتح PowerShell في مسار NTFS محلي خارج المزامنة. إذا نسخة المشروع موجودة، افحصها؛ لا تكرر clone فوقها ولا تبدلها أو تسحب تحديثاً أثناء الاختبار. لنسخة جديدة:

```powershell
git clone --branch feat/windows-laptop-testing https://github.com/overurdream-collab/test2.git
cd test2
git branch --show-current
git rev-parse HEAD
git status --short
git --version
docker version
docker compose version
docker info --format '{{.OSType}}'
wsl --version
```

المتوقع: الفرع المحدد، SHA كامل محفوظ، مصدر نظيف، Docker جاهز وOSType=linux. إذا wsl --version غير مدعوم، سجل إصدار WSL من إعدادات Windows؛ لا تغير النظام لتجاوز الفحص. سجل إصدار Windows والمتصفح، RAM والمساحة المتاحة. allocation 4 GB/2 CPU نقطة بداية من الدليل، لا SLA ولا تعديل تلقائي لإعدادات الجهاز.

## 2. التهيئة المصرح بها — LAP-03 إلى LAP-05

Start يبني الصورة ويولد ملفات مفاتيح وحسابات وبيانات اصطناعية ويكتب في DB؛ ليس قراءة فقط. إذا يوجد تثبيت سابق، راجع ملكية البيانات ومفاتيحها قبل تشغيله. لا تنسخ secrets من جهاز آخر.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Start
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Check
Invoke-RestMethod -Uri http://127.0.0.1:8000/health/ready -TimeoutSec 10
```

Bypass خاص بالعملية؛ لا تغير سياسة PowerShell العامة. عند تعارض المنفذ قبل التهيئة الأولى، استخدم Start -Port 8010 وعدّل عناوين الأوامر إلى المنفذ المسجل. المنفذ محفوظ؛ -Port جديد لا يغير تثبيتاً قائماً.

المتوقع: db وapi healthy؛ setup مؤقت؛ API منشور على 127.0.0.1 فقط دون منفذ DB؛ readiness=ready وCheck=TEST_CHECKS_PASS. أول قاعدة جديدة تحتوي 12 مطالبة أساسية. سجل زمن البناء والبدء منفصلين، فالأول يتضمن التنزيل. فشل readiness/Check يبقي الاختبار FAIL/BLOCKED حتى تتضح العلة.

فحص ACL، بعد إنشاء الملف، لا يطبع محتواه:

```powershell
(Get-Acl -LiteralPath .\deploy\laptop-private).AreAccessRulesProtected
(Get-Acl -LiteralPath .\deploy\laptop-private\.env).AreAccessRulesProtected
git check-ignore deploy/laptop-private/.env
docker compose --env-file deploy/laptop-private/.env -f deploy/compose.laptop.yml config --quiet
```

المتوقع: inheritance محمي، والملف مستبعد من Git. راجع أن قواعد الوصول للمستخدم الحالي وSYSTEM وAdministrators فقط محلياً؛ لا تنشر أسماء حسابات الجهاز. لا تعرض .env أو config الموسع أو docker inspect الكامل.

## 3. الدخول والصلاحيات — LAP-06 إلى LAP-09

في طرفية خاصة بلا transcript أو مشاركة شاشة:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Credentials
```

انقل سر كل حساب إلى Authenticator يدوياً، TOTP بستة أرقام و30 ثانية، ثم ادخل من `/login`. لا تلتقط صوراً لبيانات الدخول أو السر أو رمز TOTP. افحص الإدارة والمراجع منفصلين؛ بعد الخروج تأكد أن الصفحة المحمية تطلب الدخول. لفحص الرمز المعاد، استخدم نفس الرمز ضمن فترته؛ إن انتهت الفترة فالحالة غير حاسمة وتُعاد بعد موافقة ضمن النطاق. لا تكرر محاولات فاشلة خارج السيناريو؛ عند 429 توقف وسجلها.

فحص MFA آلي اختياري، فقط بموافقة على اختبارات المصادقة، وليس جزءاً من إعداد الوثائق:

```powershell
docker compose --env-file deploy/laptop-private/.env -f deploy/compose.laptop.yml exec -T api python -m mcias.seed.laptop check --verify-mfa
```

يختبر الحسابين ورفض الرمز المفقود/المعاد وفصل الصلاحيات، ويكتب جلسات/أحداث مصادقة. لا تكرره في نفس فترة TOTP، ولا تشغله بالتزامن مع دخول يدوي للحسابين.

لـLAP-09، استخدم job_id من رفع اصطناعي مصرح في الخطوة التالية ثم عُد لهذا الفحص. المسبار أدناه يسجل دخول الإدارة، ويطلب raw records دون field grants، ويتوقع 403، ثم يخرج ويتحقق من رفض الجلسة بـ401. هو فحص سلبي محلي مصرح، لا يمنح صلاحية جديدة. لا تحفظ token/body ولا تفعّل transcript. إذا تعذر توفير job صالح فهو BLOCKED، لا دليل نجاح من قائمة مخفية.

```powershell
$baseUrl = 'http://127.0.0.1:8000' # عدّل المنفذ فقط إذا كان مصرحاً ومسجلاً
$jobText = Read-Host 'Synthetic job_id'
$jobGuid = [Guid]::Empty
if (-not [Guid]::TryParse($jobText, [ref]$jobGuid)) { throw 'Invalid job ID' }
$protectedPassword = Read-Host 'SYN-laptop-admin password' -AsSecureString
$protectedCode = Read-Host 'Fresh TOTP code' -AsSecureString
$password = [Net.NetworkCredential]::new('', $protectedPassword).Password
$code = [Net.NetworkCredential]::new('', $protectedCode).Password
$token = $null
try {
    $payload = @{username='SYN-laptop-admin'; password=$password; totp_code=$code} | ConvertTo-Json -Compress
    $login = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/auth/login" -ContentType 'application/json' -Body $payload
    $token = $login.access_token
    $headers = @{Authorization="Bearer $token"}
    $status = 200
    try {
        Invoke-RestMethod -Uri "$baseUrl/api/v1/ingestion/jobs/$jobGuid/records" -Headers $headers | Out-Null
    } catch {
        if ($null -eq $_.Exception.Response) { throw 'Local service unavailable' }
        $status = [int]$_.Exception.Response.StatusCode
    }
    Write-Host "Protected source probe HTTP: $status"
    if ($status -ne 403) { throw 'Expected server field-access denial' }
    Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/auth/logout" -Headers $headers | Out-Null
    $revoked = 200
    try { Invoke-RestMethod -Uri "$baseUrl/api/v1/workspace/context" -Headers $headers | Out-Null }
    catch {
        if ($null -eq $_.Exception.Response) { throw 'Local service unavailable' }
        $revoked = [int]$_.Exception.Response.StatusCode
    }
    Write-Host "Revoked session HTTP: $revoked"
    if ($revoked -ne 401) { throw 'Expected revoked-session denial' }
} finally {
    if ($token) {
        try { Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/auth/logout" -Headers @{Authorization="Bearer $token"} | Out-Null }
        catch { } # قد أُبطلت الجلسة بالفعل؛ لا تطبع الاستثناء أو الرمز
    }
    $password=$code=$payload=$token=$login=$headers=$null
    $protectedPassword.Dispose()
    $protectedCode.Dispose()
}
```

قيم 401/404/503 في فحص المصدر ليست 403 المتوقعة؛ وثّق السبب ولا تعدها PASS. لا تستخدم أسماء أو ملفات حقيقية لهذا المسبار.

## 4. الواجهات — LAP-10 إلى LAP-12

افتح `/admin/dashboard` و`/institution/dashboard` في جلسة صحيحة. جرّب AR/EN وLight/Dark وTab وShift+Tab وEnter وEscape. افحص عرضاً مكتبياً ثم 768 px و390 px في أدوات المتصفح؛ سجل الأبعاد الفعلية. يجب ألا يتجاوز عرض المستند الشاشة؛ يجوز تمرير الجدول داخل حاويته. صوّر حالات الصفحة فقط ببيانات اصطناعية.

لا تستخدم `?demo=1` كدليل تكامل API. يمكن معاينة demo بعد موافقة، لكن نتائجها تسجل منفصلة؛ تحقق من شارة العرض الاصطناعي. حالات unavailable/partial يجب أن توافق مصفوفة التغطية، ولا تعامل الزر المعطل كقدرة منفذة.

## 5. المدخلات والتقارير — LAP-13 إلى LAP-18

بموافقة إدخال اصطناعي، استخدم `/admin/reference-data` لإنشاء عقد draft وتسعيرة وفئة وانتساب رمزي؛ سجل المراجع والتواريخ والعملة. العقد لا يتحول approved بمجرد رفعه. لا تنشئ ملفات مصدر جديدة أو تضف حقول هوية حقيقية دون موافقة مستقلة.

الـ12 مطالبة الأساسية مصدرها metadata-only، و`demo.json` معاينة واجهة؛ لا يوفران ملفات أصل جاهزة للرفع. ملفات `synthetic-workflow.csv` و`synthetic-invalid.xlsx` يولدها هارنس التكامل أثناء تنفيذه، ولا تأتي كملفات جاهزة في clone. لا تشغّل ذلك الهارنس على قاعدة اللابتوب لإحضارها؛ يحتاج بيئة واختبارات مستقلة. يلزم ملف اختبار متاح وموافق عليه أو إذن صريح لتوليده قبل حالات الرفع والحجر.

ارفع المصدر الاصطناعي الموجود والموافق عليه من `/admin/ingestion`، وسجل SHA وdocument_id وjob_id وmanifest. كرر نفس الملف لاختبار duplicate؛ ارفع الملف التالف الموجود فقط لاختبار الحجر. جهز دفعة من المصدر الصالح من `/institution/claims/batches` واستأنفها، ثم أعد resume وقارن العدد. العودة إلى LAP-09 تتطلب job صالحاً من هذه المرحلة.

بديل آلي مصرح لإدخال عينة مراجع ومطالبة واحدة وفحص MFA:

```powershell
docker compose --env-file deploy/laptop-private/.env -f deploy/compose.laptop.yml exec -T api python -m mcias.seed.laptop check --verify-mfa --verify-inputs
```

هذا الأمر يولّد ويرفع `SYN-laptop.csv` ويضيف بيانات؛ يلزم إذن يشمل ذلك. يحفظ إيصال `laptop-smoke.json` خاصاً لفحص الاستمرارية. لا تكرر الأمر لمجرد فحص الخدمة. لا يغطي duplicate/quarantine أو كل سيناريوهات الخطة. عند نقص ملف التالف أو أدواته، سجل LAP-16 BLOCKED واطلب الإذن المناسب؛ لا تولده تلقائياً.

في `/institution/reports` راجع snapshot والعملة والبصمة والمصدر والـheld، وأنشئ إصداراً اختبارياً جديداً للدفعة المضافة فقط إذا كان ذلك مصرحاً. لا تتوقع أن تتغير لقطة التقرير القديم عند إضافة مطالبة. تصدير PDF/Excel المسموح بيانات اصطناعية فقط؛ احفظه محلياً في نطاق الدليل المعتمد، وسجل SHA-256 باستخدام Get-FileHash. الرفع/التقرير ليسا تشغيل G5 إنتاجياً أو موافقة دفع.

## 6. الاستمرارية والموارد — LAP-19، LAP-20

سجل أعداد ومراجع المطالبات/العقد/التقرير قبل الإيقاف، ثم:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Stop
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Start
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\laptop.ps1 -Action Check
docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' mcias-laptop-api-1 mcias-laptop-db-1
docker image inspect mcias-laptop:local --format '{{.Id}}'
docker compose --env-file deploy/laptop-private/.env -f deploy/compose.laptop.yml exec -T api python --version
docker compose --env-file deploy/laptop-private/.env -f deploy/compose.laptop.yml exec -T db postgres --version
```

قارن نفس المراجع والأعداد بعد Start، وأعد الدخول للحسابين برمز جديد. Check يفحص المطالبة الإضافية تلقائياً إن وجد إيصال الفحص الآلي. للمطالبات اليدوية قارن مراجعك أنت. Start يعيد البناء؛ لا يحدث Git تلقائياً، لكن التنزيل/اعتماديات البناء قد تغير image ID، لذلك سجله قبل وبعد. ذاكرة الحاويات لا تشمل Windows/WSL؛ سجل Task Manager أيضاً وتوقيت القياسات. لا تشغّل حمل 10K على نفس القاعدة.

## 7. الأعطال والإغلاق — LAP-21 إلى LAP-24

عند BLOCKED، احتفظ باسم الخطوة والحالة وSHA وبيئة الجهاز ودليل منقح. لا تنشر logs خاماً؛ الاستثناءات قد تتضمن بيانات. أوقف التجربة عند فقد البيانات أو كشف سر أو تجاوز صلاحية. Stop يحفظ volumes لكنه تعديل لحالة الخدمات؛ استخدمه ضمن موافقة الجولة، ولا توقف تطبيقات أخرى.

لا down -v ولا حذف .env ولا تبديل مفاتيح فوق قاعدة قائمة. الاستعادة وإعادة الضبط والإصلاحات تحتاج موافقة وخطة منفصلة وفق [دليل التعافي](G9_DISASTER_RECOVERY_AR.md). سجل القدرات خارج النطاق كما في الخطة، وأكمل التقرير ومراجعته. قرار الدمج HOLD حتى اكتمال الحالات الأساسية وموافقة المستخدم؛ لا ترفع GATE_STATUS إلى ACCEPTED.
