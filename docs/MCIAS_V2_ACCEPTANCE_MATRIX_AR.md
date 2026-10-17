# MCIAS v2.0 — مصفوفة الاختبارات والقبول لسجل المدخلات والتدقيق

**الوضع:** متطلبات وإثباتات هندسية. **كل البوابات المؤسسية G0–G9 مفتوحة**. لا تعني أي نتيجة PASS السماح بنقل بيانات المرضى أو تشغيل صرف/رفض حقيقي.

## طريقة قراءة هذه المصفوفة
- `IMPLEMENTED_AND_TESTED`: توجد شيفرة واختبار فعلي في هذه النسخة، ويجب الرجوع لنتيجة GitHub Actions على SHA.
- `IMPLEMENTED_NEEDS_UAT`: الوظيفة موجودة لكن يلزم اختبار استخدام مؤسسة أو أدوار بشرية مستقلة.
- `PARTIAL`: تنفيذ جزئي لا يغطي العقد الوظيفي كاملًا.
- `NOT_IMPLEMENTED`: غير موجود، ولا يصح وصفه بغير ذلك.
- `BLOCKED_INSTITUTION`: يتوقف على تفويض/توقيع/سياسة أو مراجع معتمدة.

| ID | مجال التحقق | الاختبار الإلزامي أو الشرط | حالة هندسية | مصدر الإثبات / الملاحظات |
|---|---|---|---|---|
| REF-01 | تقسيم المدخلات | ظهور الأقسام الثمانية دون خلط الشروط | IMPLEMENTED_NEEDS_UAT | `reference_points_view.js`; فحص مؤسسي للشاشة مطلوب |
| REF-02 | البنود الفعلية | بند مدة العقد، ألف مستفيد، واستثناء العلاج خارج البلد كنقاط مستقلة | PARTIAL | النموذج النصي يحفظها؛ الاستخراج من ملفاتها آليًا غير منفذ |
| REF-03 | مصدر الملف | رفع PDF/XLSX عبر G2 وحفظ المصدر والبصمة | IMPLEMENTED_NEEDS_UAT | `ingestion.api` القديم؛ ليس Parsing للمادة التعاقدية |
| REF-04 | اليدوي | إضافة بند عبر الواجهة ينشئ `draft` فقط | IMPLEMENTED_AND_TESTED | `reference_points.py` و`test_temporal_point_persistence.py` |
| REF-05 | الصلاحيات | قراءة فقط لا تسمح بالإضافة/الاعتماد، ومنع المؤسسة الأخرى | IMPLEMENTED_AND_TESTED | `test_reference_points_http_security.py` |
| REF-06 | عدم الحذف | منع حذف المعتمد وتعديل نصه أو تعريفة النسخة القديمة | IMPLEMENTED_AND_TESTED | ORM/PostgreSQL trigger + `test_temporal_point_persistence.py` |
| REF-07 | الاستبدال | تاريخ إغلاق النسخة القديمة = بداية الجديدة (نهاية حصرية) | IMPLEMENTED_AND_TESTED | `ReferencePointClosure` + حالات الاختبار |
| REF-08 | التاريخ القديم | قبل يوم التعديل = القديم، وفي يوم التعديل = الجديد | IMPLEMENTED_AND_TESTED | `test_reference_rule_bridge.py` |
| REF-09 | مقدم خدمة مستقل | مستشفى H1 بسعرين بحسب التاريخ وH2 بسعر ثالث ثابت | IMPLEMENTED_AND_TESTED | اختبارات تكامل `reference_rule_bridge` |
| REF-10 | العملة وDecimal | اختلاف عملة أو سعر G3/G5 والبند الجديد يسبب حجزًا | IMPLEMENTED_AND_TESTED | `reference_rule_bridge.py` و`audit_engine.py`؛ اختبار G3/G5 قائم |
| REF-11 | غياب المصدر | عند عدم وجود بند جديد لا نستبدل G3 أو نخترع تعرفة | IMPLEMENTED_AND_TESTED | `reference_rule_bridge.py`؛ تكامل G5 |
| REF-12 | شروط نصية | «العلاج خارج الدولة غير مشمول» لا يُحوّل إلى خصم تلقائي دون حقل بلد الخدمة | PARTIAL | المنطق الحالي يضع بنود الاستثناء غير المعروفة في مراجعة؛ الاختبار المتكامل يغطي الموافقات المسبقة غير المفسرة، لا هذا المثال السريري حرفيًا |
| REF-13 | نطاق الفئة | ربط الفئات والمستفيدين بدليل عضوية مكتمل ومعتمد | PARTIAL | G3 يدعم أهلية زمنية؛ إثبات اكتمال القائمة غير منفذ |
| REF-14 | التحقق المستقل | لا حساب إذا تعارضت المدخلات؛ Palermo يفحص الأرقام والبصمة | IMPLEMENTED_AND_TESTED | `audit_service.py`, `palermo2.py`; ملحق الأدلة `reference_reconciliation` |
| REF-15 | رفض قطعي | عدم وجود شخص **بسجل مستفيدين كامل رسميًا** → رفض مثبت | NOT_IMPLEMENTED | G5 يضع `hold` عند الغياب؛ لا يُعد الفشل قطعيًا |
| REF-16 | مستند ناقص | مرفق مطلوب غير موجود → ملف مرفقات ناقصة | IMPLEMENTED_AND_TESTED | `claim_outcomes.py` واختبار فئات الأربع |
| REF-17 | مقبول مشروط | 8 فحوص PASS + Palermo verified + لا تعارض بنود زمنية | IMPLEMENTED_AND_TESTED | تصنيف `ACCEPTED_RULES` أولي، ليس دفعًا |
| REF-18 | بشري | مرجع متعارض أو غير مفسّر أو لقطة غير موجودة → مراجعة | IMPLEMENTED_AND_TESTED | `claim_outcomes.py` |
| REF-19 | التصدير الحصري | كل مطالبة تظهر في ملف واحد من الأربعة للدفعة المحددة | IMPLEMENTED_AND_TESTED | `claim_outcomes.classify_claims` + اختبار |
| REF-20 | CSV آمن | منع Excel formula injection في النصوص المُصدرة | IMPLEMENTED_AND_TESTED | `export_csv` واختبار صيغة تبدأ بـ`=` |
| REF-21 | تاريخ الإعادة | إعادة التدقيق نسخة مستقلة، لا تعديل نتيجة قديمة | PARTIAL | G6 إعادة التدقيق موجودة؛ الربط الكامل بإصدارات البنود يحتاج UAT |
| REF-22 | استخراج AI | رفع عقد ثم AI يستخرج البنود والأدلة والمواضع تلقائيًا | NOT_IMPLEMENTED | مطلوب في مرحلة Contract Intelligence مستقلة |
| REF-23 | الاعتماد الإنتاجي | توقيع مفوض مرتبط `SHA256` للبند + فصل مراجعين | BLOCKED_INSTITUTION | Production fail-closed حاليًا؛ لا إقرار عام كافٍ |
| REF-24 | تعرفة G3 الحقيقية | النقل بين إصدارات العقود الموقعة مع تعديل أسعار المستشفى | PARTIAL | توفيق قراءة فقط؛ لا استبدال G3 ماليًا من البنود الجديدة |
| REF-25 | تعريف كل شرط | مترجم Typed Clause لجميع العقود، الاستثناءات، الموافقات، الفئات | NOT_IMPLEMENTED | يجب تحديد قواعد/أولويات معتمدة لكل نوع ومقارنتها بالنص |
| REF-26 | الوكلاء A1–A5 | تشغيل نموذج AI وتفسير تضخيم/ترميز/طب | NOT_IMPLEMENTED | مهمة الوكلاء المنفصلة؛ ليست ضمن هذا PR |
| REF-27 | كلفة وفورات معتمدة | حساب المسترد/الموفر الفعلي دون ازدواج | NOT_IMPLEMENTED | لا يُستنتج من الملفات الأربعة |
| REF-28 | التزام إنتاجي | توقيع المؤسسة وخصوصية بيانات وشهادات تشغيل | BLOCKED_INSTITUTION | G0–G9 مفتوحة |
| REF-29 | تزامن وسباق | قفل البند على PostgreSQL عند التعديل ورفض تداخل الفترات | PARTIAL | advisory lock / unique؛ اختبار تنافس متعدد الاتصالات لا يزال مطلوبًا |
| REF-30 | عرض كثيف | تاريخ سريان يُرشح قبل pagination، وتجاوز 100 نقطة منطبقة يحجز | PARTIAL | التنفيذ موجود، لكن اختبار ضغط/ترقيم يتجاوز 100 بند لا يزال مطلوبًا |

| REF-31 | حماية SQL المباشر | منع INSERT approved وUPDATE/DELETE عبر PostgreSQL trigger | IMPLEMENTED_AND_TESTED | `test_reference_points_postgres.py` على PostgreSQL وليس ORM فقط |
| REF-32 | تكامل سياسة موقعة | صلاحية G5 مستقلة وصحيحة، لكن شرط موافقة مسبقة غير مفسر → HOLD دون خصومات | IMPLEMENTED_AND_TESTED | `test_run_audit_immutable_snapshot_captures_reference_block`، بصمة السياسة وPalermo وفئة REVIEW |

## معايير الخروج قبل الدمج إلى main
1. جميع GitHub Actions عند **آخر SHA** ناجحة، وتشمل الوحدة وPostgreSQL وواجهة المؤسسة وG8 وG9 والأمن.
2. مراجعة مستقلة للـAPI وقيود PostgreSQL ومفاتيح البيانات والفصل بين المؤسسات.
3. التوثيق هذا ودليل البدء وسجل التنفيذ متوافق مع الكود الفعلي وأرقام الهجرات.
4. لا توجد وظيفة مذكورة «مكتملة» وهي جزء تجريبي فقط؛ لا تُعد نجاحات CI اعتمادًا مؤسسيًا.
5. لا دمج أو نشر من هذه الوثائق دون موافقة صاحب المشروع وفحص الأثر الأمني والمالي.

## اختبار ما قبل A1
- المطالبة التاريخية للمستشفى H1 تمر على G3 وG5 وفق تاريخها؛ لا تستخدم سعر H2.
- بند جديد صادر بعد تاريخ الخدمة لا يُغيّر نتيجة لقطات G5 السابقة.
- بند جديد متعارض مع G3 أو أي بند نصي غير مفسر يعلق النتيجة ويظهر مرجعها في اللقطة وفي ملف نتائج التدقيق.
- أي AI لا يملك سلطة تحويل `HOLD` إلى قبول أو رفض، ولا تغيير `policy_fingerprint`.


### Contract Intelligence addendum — feature branch PR #23
| ID | Gate | Status | Evidence |
|---|---|---|---|
| CI-01 | Source quote locator and numeric validator (pure module) | IMPLEMENTED_NOT_TESTED | mcias/contract_intelligence.py; tests/test_contract_intelligence.py, PENDING_CI |
| CI-02 | On-prem model HTTP transport configured locally | IMPLEMENTED_NOT_TESTED transport only | no configured runtime or live inference |
| CI-03 | Tenant-scoped API, persistent proposal, reviewer UI | NOT_IMPLEMENTED | No routes or migration on C1 |
| CI-04 | Synthetic Arabic/English/OCR dataset and Precision/Recall | NOT_IMPLEMENTED | no model inference / reference gold |
| CI-05 | Typed approved financial compiler and signature | NOT_IMPLEMENTED / BLOCKED_INSTITUTION | G3/G5 authority preserved |

| CI-06 | RBAC + tenant + per-field gate preview API | IMPLEMENTED_NEEDS_CI | tests/test_contract_intelligence_api.py, 7 synthetic unit/HTTP scenarios; PENDING_CI |
| CI-07 | Preview button linked into existing bilingual workspace | IMPLEMENTED_NEEDS_UAT | mcias/web_workspace/reference_points_view.js; model unconfigured by default |
| CI-08 | Redirect-proof local inference | IMPLEMENTED_NEEDS_CI | numeric loopback only + HTTP no-follow; test setup pending |

| CI-09 | Actual synthetic PDF two pages + XLSX H1/H2/H3 + scanned quarantine + injection-as-text | IMPLEMENTED_NEEDS_CI | tests/test_contract_documents.py, PENDING_CI, not AI inference |

| CI-10 | Type whitelist for tariffs/copay, source/date/tenant scope, forged AST guard | IMPLEMENTED_NEEDS_CI | mcias/contract_rule_compiler.py tests/test_contract_rule_compiler.py; DIAGNOSTIC_ONLY, never financial authority |

### Contract Intelligence C6 (new SHA CI pending)
| ID | Scope | State |
|---|---|---|
| CI-C6-01 | Persist tenant/source-bound AI candidates without activation | IMPLEMENTED_NOT_TESTED |
| CI-C6-02 | Independent one-time review, deny cross-tenant and bad OCR | IMPLEMENTED_NOT_TESTED |
| CI-C6-03 | Promote reviewed complete candidate to draft only | IMPLEMENTED_NOT_TESTED |
| CI-C6-04 | PostgreSQL 0020 append-only triggers | IMPLEMENTED_NOT_TESTED |
| CI-C6-05 | Real Qwen inference, Arabic/mixed gold Precision and Recall | NOT_MEASURED |
| CI-C6-06 | Human reviewer UI and institution-bound signature | PARTIAL / BLOCKED_INSTITUTION |


### C8 reviewer UI / real pretrained benchmark (PENDING_CI)
| ID | Evidence requirement | State |
|---|---|---|
| CI-C8-01 | Bilingual source-linked extraction-save UI and independent reviewer UI pass browser tests | IMPLEMENTED_NOT_TESTED |
| CI-C8-02 | Pinned Qwen3-0.6B downloads and generates in free CPU Actions; actual response SHA | PENDING_CI / NOT_YET_MEASURED |
| CI-C8-03 | Synthetic Arabic, English, mixed, prompt-injection TP/FP/FN, Precision/Recall | PENDING_CI / NOT_YET_MEASURED |
| CI-C8-04 | Gold 20+ files including Arabic OCR, tables and amendment/medical cases | NOT_IMPLEMENTED |
| CI-C8-05 | Institutional signatures/approval and production | BLOCKED_INSTITUTION |


### C10 model grammar and PostgreSQL negative tests (PENDING_CI)
| ID | Actual evidence and requirement | State |
|---|---|---|
| CI-C10-01 | JSON schema constrained local model transport (official MIT LMFE) | IMPLEMENTED_NOT_TESTED |
| CI-C10-02 | Real Qwen3-0.6B produces verifiable English/Arabic/mixed candidate | FAILED at C9; C10 PENDING_CI |
| CI-C10-03 | Injection source never becomes financially executable even with valid JSON | Source validator only; real adversarial C10 PENDING_CI |
| CI-C10-04 | Raw PostgreSQL updates and deletions forbidden on proposal, review and promotion | IMPLEMENTED_NOT_TESTED |
| CI-C10-05 | 20+ synthetic real PDFs/OCR/XLSX gold, Precision/Recall and independent clinical/legal review | NOT_COMPLETE |


### C13 gold corpus and C12 objective evaluation
| ID | Acceptance check | Status |
|---|---|---|
| CI-C13-01 | Twenty SYN exact quotes across all eight contract/reference sections | IMPLEMENTED_NOT_TESTED |
| CI-C13-02 | Ten adversarial corruptions rejected as source-unverified | IMPLEMENTED_NOT_TESTED |
| CI-C13-03 | Pinned Qwen3-1.7B obtains any source-backed clause in four-SYN CPU trial | FAIL at d33c245: TP0 FP0 FN3 / Recall0 / Precision undefined |
| CI-C13-04 | 20+ actual contract files with Arabic OCR + table model predictions and gold metrics | NOT_MEASURED |
| CI-C13-05 | Enterprise rate limiter / browser combined suite on exact SHA | FAIL at d33c245 (1 rate limit test), rerun requested |
| CI-C13-06 | Production financial activation approved/signed independently | BLOCKED_INSTITUTION |


### C15 date source contract
| ID | Gate | State |
|---|---|---|
| CI-C15-01 | Date elsewhere on same PDF page cannot authorize an unrelated quoted tariff | IMPLEMENTED_NOT_TESTED |
| CI-C15-02 | Date from same XLSX row is permitted if other source fields match | IMPLEMENTED_NOT_TESTED |
| CI-C15-03 | Purely invented dates cause needs_human_review | IMPLEMENTED_NOT_TESTED |
| CI-C15-04 | Real-world cross-referenced header/annex date provenance workflow | PARTIAL / MANUAL_REVIEW |


### C16 model instruction regression
| ID | Gate | Current status |
|---|---|---|
| CI-C16-01 | No provider/amount/date constants copied from system prompt examples | IMPLEMENTED_NOT_TESTED |
| CI-C16-02 | XLSX same-row date fixture / independently reviewed source end date | IMPLEMENTED_NOT_TESTED |
| CI-C16-03 | Real Qwen3-1.7B source-backed clause extraction in four-SYN diagnostic | FAIL at C14: 4 quarantined, TP0 FP0 FN3; C16 retest PENDING |
| CI-C16-04 | Full G1–G9 + Enterprise at C16 exact SHA | PENDING_CI; C15 G1–G7/Enterprise FAILED |

### C19 multiprovider PDF quote boundary
| ID | Test | Status |
|---|---|---|
| CI-C19-01 | Same PDF page shows H1 and H2 price; H2 cannot be bound to H1 quote | IMPLEMENTED_NOT_TESTED |
| CI-C19-02 | Same page shows CONSULT and XRAY USD; quote-specific service/currency required | IMPLEMENTED_NOT_TESTED |
| CI-C19-03 | Structured XLSX same source row fields may carry identities separately | IMPLEMENTED_NOT_TESTED; existing reader tests remain |
| CI-C19-04 | Model-derived tariff financial execution | BLOCKED_INSTITUTION / NOT_AUTHORIZED |

### C20 synthetic full-file reader acceptance gates
| ID | Requirement | Current status |
|---|---|---|
| CI-C20-01 | Ten separate real three-page PDF SYN contracts yield page-specific terms | IMPLEMENTED_NOT_TESTED |
| CI-C20-02 | Five distinct real XLSX SYN price files keep H1/H2/H3 separate | IMPLEMENTED_NOT_TESTED |
| CI-C20-03 | Five real scanned PDFs without OCR quarantine rather than guess clauses | IMPLEMENTED_NOT_TESTED |
| CI-C20-04 | Local Arabic OCR accuracy on scanned PDF with source rows | NOT_MEASURED |
| CI-C20-05 | Real LLM correctly extracts 20+ actual full documents; precision/recall | NOT_MEASURED |

 
### Contract Intelligence C22 objective gate
| ID | Requirement | Status |
|---|---|---|
| CI-C22-01 | Explicit local CPU transport 180s cap; default 30s; reject 0/181 | IMPLEMENTED_PENDING_CI |
| CI-C22-02 | Pretrained Qwen2.5-1.5B text inference delivers at least one source-verified clause within configured test deadline | C21 FAIL (timeout at 60s); C22 NOT_MEASURED |
| CI-C22-03 | 20 binary synthetic source reader documents + 20 text anchors/10 adversarial validator cases | EXISTING (regular C21 CI PASS); not AI precision/recall |
| CI-C22-04 | Measured human-reviewed bilingual, Arabic OCR 20+ doc model Precision/Recall | NOT_MEASURED |
| CI-C22-05 | Institutional signed financial execution or PR merge | BLOCKED_NO_AUTHORIZATION |
