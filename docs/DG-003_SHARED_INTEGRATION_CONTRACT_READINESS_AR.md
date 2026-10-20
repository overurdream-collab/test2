# MCIAS v2.0 — DG-003: Shared Integration Contract & Readiness

**التاريخ:** 20 أكتوبر 2026  
**المالك التصميمي:** L2 — Integration Lead + Alembic Compatibility Owner  
**القرار:** `DESIGN READY FOR INDEPENDENT REVIEW` / **التكامل التشغيلي لا يزال BLOCKED**  
**حدود التنفيذ:** READ-ONLY — لا تعديل كود، لا ترحيلات، لا إنشاء فرع، لا Merge، لا Deploy، ولا اتصال بقاعدة إنتاجية.

## 0 — نطاق التثبيت ومصادر الحقيقة

فُحصت أحدث رؤوس GitHub التالية خلال إعداد التقرير. لا تُنقل نتائج CI بين SHAs أو فروع مختلفة:

| المكون | الفرع | SHA المثبت |
|---|---|---|
| main | `main` | `b69defa2f621458ef44d790b510840307a81009a` |
| A1 / PR #20 | `feat/mcias-a1-invoice-integrity` | `6af41a04cf887d389656c9ce7ffc4e03b396b5a4` |
| Contract Intelligence / PR #23 | `feat/mcias-contract-intelligence` | `16cc288e8c71eeb5731f36fe39a16e617e6f3483` |
| Unified Inputs / PR #25 | `feat/mcias-input-triactions-e2e` | `8a616f7f68f506df08deccd62a9faa7d7ec89272` |
| Shared Audit / PR #29 | `feat/mcias-shared-audit-writer-phase1` | `fd1bb1d22f1957f40688baa207cdf449b0690cd9` |
| Document Reader | `feat/mcias-document-reader-isolated-pilot` | `36e03751d71306f33ee50ce4e0dea879e2a4b3c2` (HEAD عند التسليم؛ المرجع التاريخي عند إعداد التقرير: `fbac4afb34c8136681adf37aefda3975912dac4c`) |
| L2 scoped experimental composition / PR #28 | `integration/mcias-l2-shared-audit` | `65bbddc1ae95aed22e157774f600a296a6e43926` |

**مراجعة سابقة، دون إعادة جرد:** [DG-001 Alembic Compatibility في PR #25](https://github.com/overurdream-collab/test2/blob/8a616f7f68f506df08deccd62a9faa7d7ec89272/docs/DG-001_ALEMBIC_BRANCH_COMPATIBILITY_READ_ONLY_20261020_AR.md). العقد الحالي لا يغير نتيجة التعارض المؤكدة ولا يدعي تجربة تشغيل مشتركة.

---

## 1 — Shared Audit Unified Contract v1 (مقترح للمراجعة)

### 1.1 المرجع والتوافق

**مرشح المرجعية:** PR #29 (مع حماية التوافق للمستهلكين)، وليس استبدالًا تشغيليًا معتمدًا. النسختان تقدمان توقيعَي Python نفسيهما:

```python
write_event(db, *, actor, organization_id, action, resource_type, resource_id, outcome, details=None)
record_outcome_independent(bind, *, actor_id, organization_id, action, resource_type, resource_id, outcome, details=None)
```

- المصدر الأساسي PR #25: [`mcias/audit_writer.py`](https://github.com/overurdream-collab/test2/blob/8a616f7f68f506df08deccd62a9faa7d7ec89272/mcias/audit_writer.py)؛ بصمة Blob `509ce4124f012cc4a121294fe9122c9384902fd6`.
- مرشح PR #29: [`mcias/audit_writer.py`](https://github.com/overurdream-collab/test2/blob/fd1bb1d22f1957f40688baa207cdf449b0690cd9/mcias/audit_writer.py)؛ بصمة Blob `e17f58b06d191b28f9eaff340feeff0691c80edf`، ويستدعي [`mcias/audit_contract.py`](https://github.com/overurdream-collab/test2/blob/fd1bb1d22f1957f40688baa207cdf449b0690cd9/mcias/audit_contract.py)؛ Blob `88af554c6402679a2b87aa37b1268876c3507fde`.

| البند | PR #25 الفعلي | PR #29 الفعلي | عقد DG-003 المقترح |
|---|---|---|---|
| دوال الكاتب | الدالتان | نفس التوقيعين | الحفاظ عليهما وعدم كسر المستهلكين |
| `action` | طول ≤120 وغير فارغ | lowercase snake_case، `^[a-z][a-z0-9_]{0,119}$` | أسماء معرّفة خادميًا، وفق PR #29 |
| `resource_type` | طول ≤90 وغير فارغ | `^[a-z][a-z0-9_]{0,89}$` | قائمة أنواع معتمدة |
| `resource_id` | بلا تحقق صيغي خاص في الكاتب | NULL أو معرّف opaque لا يتجاوز 36 حرفًا | خادمي فقط، وفحص أي معرّفات قديمة قبل التبديل |
| `outcome` | success / denied / error | القيم نفسها | ثابت كما هو |
| `details.reason_code` | أي قيمة بسيطة حتى 150 حرفًا | قائمة أسباب معتمدة، وإلا تُحذف | قائمة ثابتة مع اختبار لكل حدث |
| `version` | قيمة بسيطة وقد تكون bool/string | عدد صحيح 0..999999999 | نوع صحيح إلزامي عند استخدامه |
| `status` | نص بسيط بطول محدد | قائمة حالات مغلقة | تعيين حالات صحيحة لكل مستهلك |
| `effective_from/until` | نص بسيط | تاريخ ISO صالح | توحيد تاريخ الحقل |
| `contract_number` | قد يُحفظ كنص | يُحذف حفاظًا على الخصوصية | عدم اعتباره حقل Audit مضمونًا |
| حقول PHI وكلمات المرور والنص الحر | بعض الحقول غير المعروفة تُحذف | ترشيح نوعي أشد | لا تُرسل أصلًا، مع اختبارات عدم التسرب |
| فحص الممثل والمؤسسة | يفرض Actor نشطًا ومطابقًا للمؤسسة | الشرط نفسه | Actor ومؤسسة موثوقان من الخادم، لا من جسم الطلب |
| RBAC الفعلي | ليس مسؤولية الكاتب | ليس مسؤولية الكاتب | حارس/خدمة الـAPI تفحص الصلاحيات قبل الكاتب |
| آلية idempotency | غير موجودة في الكاتب | UUID helper غير محفوظ | **غير معتمدة** حتى إضافة ربط وقيود DB واختبارات سباق |

**ملاحظتان أمنيتان:** (1) إسقاط حقل من `details` دون خطأ ليس ضمانًا بأن الحقل المطلوب للتتبع قد حُفظ؛ يجب اختبار البيانات الوصفية **المسموح بها والمطلوبة**. (2) صلاحية المستخدم لا تُمنح لمجرد أن الكاتب قبِل Actor مطابقًا للمؤسسة؛ RBAC يُثبت قبل استدعاء الكاتب.

### 1.2 هيكل الحدث المنطقي v1

**حقول ثابتة مطلوبة في الحدث التشغيلي المقترح:** `event_id` خادمي ثابت، `request_attempt_id` خادمي لكل محاولة HTTP، `actor_id` المثبت من الجلسة، `organization_id` الخادمي، `action`، `resource_type`، `resource_id` (nullable عند عدم وجود مورد موثوق)، `outcome`، `reason_code` خادمي مغلق عند الرفض، وقت التسجيل، ومعرّف العملية `operation_id` **إذا كانت عملية أعمال قابلة لإعادة الطلب**. لا ينقل هذا العقد تفاصيل طبية أو كلمات مرور أو مستندات إلى Audit.

**التمييز الضروري:** `request_attempt_id` يختلف بين محاولتي HTTP حتى عند إعادة استخدام `operation_id`، بينما `operation_id` يحدد إعادة نفس أمر الأعمال؛ لا يجوز دمج محاولتي رفض HTTP منفصلتين في حدث واحد.

**الوضع الحالي:** PR #29 يوفّر `new_request_attempt_id()` كمولد UUID منفصل، **دون middleware أو تخزين أو UNIQUE**. لا ينبغي الادعاء أن الحقول والقيود المقترحة كلها موجودة في الجدول أو الكاتب الحالي.

### 1.3 ملكية المعاملة ومنع تكرار الحدث

| الحالة | مالك القرار | موضع الكتابة | القاعدة |
|---|---|---|---|
| نجاح أعمال/قبول مراجعة OCR | خدمة المجال | `write_event(db, ...)` داخل معاملة الأعمال | commit واحد للأعمال والحدث أو rollback لكليهما |
| رفض صلاحية HTTP 403 | حارس الصلاحيات يقرر، **مالك معاملة HTTP** يكتب | rollback أولًا، ثم `record_outcome_independent(bind, ...)` | **حدث أمني واحد** لكل قرار رفض لمحاولة HTTP |
| تعارض أعمال 409 بعد مصادقة ناجحة | مالك خدمة المجال | rollback ثم حدث domain-denied واحد | لا يُسجّل كرفض RBAC 403 إضافي |
| مستخدم مجهول/جلسة غير مثبتة | سياسة أمن وهوية منفصلة | **لا كاتب قائم معتمد** | لا اختلاق Actor أو Tenant، ولا تسجيل غير موثوق |
| فشل Audit عند flush/commit | مالك الكاتب / مالك الطلب | فشل معلن دون تثبيت أعمال | لا إخفاء الخطأ أو الادعاء أن Audit نجح |
| ضياع تأكيد commit / الحالة UNKNOWN | مالك الكاتب والتسوية | الاستعلام عن `event_id` ثابت قبل أي إعادة | لا تفترض rollback ولا تكتب حدثًا بديلًا تلقائيًا |

**اقتراح منع الازدواج:** إسناد قرار الرفض الواحد إلى `decision_key` خادمي داخل `request_attempt_id`، وربطه بقيد تفرد على `(request_attempt_id, decision_key)` مستقبلًا بعد اعتماد المخطط. إذا تطلب المجال حدثين أمنيين **مختلفين فعليًا** في طلب واحد، يجب تعريف قراري تفويض منفصلين بوضوح، لا تكاثر استدعاءات الكاتب لنفس القرار. `event_id` ثابت قبل محاولة الحفظ ويُستخدم في تسوية UNKNOWN. لا يمثل هذا توصيفًا لقيد مُنفذ حاليًا.

### 1.4 قاموس الحدث v1 — خاضع لتصديق الملاك

| المستهلك | `action` في الكود القائم | نوع المورد | صلاحية الحدث |
|---|---|---|---|
| G2 | `source_ingested` | `ingestion_document` | نجاح إدخال مستند (كاتب قديم مباشر) |
| PR #25 إنشاء عقد | `contract_draft_created` | `contract_version` | success داخل الأعمال |
| PR #25 تعديل عقد | `contract_draft_revised` | `contract_version` | success داخل الأعمال |
| PR #25 رفض إنشاء | `contract_creation_denied` | `contract_version` | denied؛ 403 أو 409 حاليًا، يلزم فصل مالك الحدث |
| PR #25 رفض تعديل | `contract_revision_denied` | `contract_version` | 409 من خدمة المجال؛ 403 من مالك HTTP |
| PR #25 input clauses | `input_clause_draft_created`, `input_clause_version_activated` | متعلق بالبند | كاتب قديم مباشر، يحتاج توافق لاحق |
| Reader التجريبي | `ocr_transcription_{action}`, `ocr_transcription_denied` | `ocr_candidate` | نجاح/رفض نقل نص، لا اعتماد طبي |
| L2 العام | `permission_denied`, `tenant_access_denied` | وفق الحارس | 403 خادمي واحد بعد rollback |
| A1 | **لا يوجد استدعاء مباشر مثبت للكاتب المشترك** في واجهة A1 الحالية | — | حالة استشارية؛ لا نخترع حدثًا ناجحًا قائمًا |

**التعارض المؤكد:** PR #25 `create_contract()` يسجّل `contract_creation_denied` بعد rollback عند HTTP 403، بينما تركيب L2 يميل لتسجيل `tenant_access_denied` عند التقاط `AuthorizationDenied` نفسه في `get_db()`. قد ينتج حدثان من محاولة واحدة. **STOP** حتى يعتمد PR #25 وL2 مسارًا واحدًا. استدعاء `_actor()` في `revise_contract()` يقع قبل `try/except` المحلي؛ ومسار 409 داخل handler يسجّل حدث مجال. يجب اختبار كليهما على التطبيق المركب.

---

## 2 — Consumer Compatibility Matrix

| المستهلك / موقع المصدر | الاستدعاء الفعلي | قابلية اعتماد PR #29 مباشرة | خطر التوافق | اختبار القبول المقترح ومالكه |
|---|---|---|---|---|
| **G2** — [`mcias/ingestion/orchestrator.py`](https://github.com/overurdream-collab/test2/blob/b69defa2f621458ef44d790b510840307a81009a/mcias/ingestion/orchestrator.py) | `db.add(AuditLog(action="source_ingested", details={sha256,status}))` ثم `db.commit()` | **لا يستخدم API الكاتب** | تغيير التسجيل قد يفقد SHA من Audit بسبب سياسة ترشيح PR #29؛ الأصل يحتفظ به G2 | عدم تغيير إدخال G2، اختبار عدم فقد المصدر/الحدث، RBAC وعزل المؤسسة، G2 owner + PR #29 |
| **Document Reader** — [`scripts/reader_g2_audit_a1_pg16_contract.py`](https://github.com/overurdream-collab/test2/blob/fbac4afb34c8136681adf37aefda3975912dac4c/scripts/reader_g2_audit_a1_pg16_contract.py) | كاتب PR #29 الحقيقي في تجربة: `write_event` داخل مراجعة؛ `record_outcome_independent` عند رفض محدد | **متوافق تجريبيًا فقط** | RBAC `ingestion.review` تجريبي؛ جدول ReviewVersion تجريبي؛ غياب ضمان الكاتب العام ضد التكرار | جلسة خادمية + tenant + 36 حدثًا/36 إصدار مراجعة اصطناعيًا، تزامن، replay، منع PHI؛ Reader owner + PR #29 |
| **A1 / PR #20** — [`mcias/agents/a1_api.py`](https://github.com/overurdream-collab/test2/blob/6af41a04cf887d389656c9ce7ffc4e03b396b5a4/mcias/agents/a1_api.py), [`a1_trusted_input.py`](https://github.com/overurdream-collab/test2/blob/6af41a04cf887d389656c9ce7ffc4e03b396b5a4/mcias/agents/a1_trusted_input.py) | القراءة والتحقق والحساب الاستشاري؛ لا استخدام مباشر للكاتب في الملفات المفحوصة | **لا عقد كتابة قائمًا** | الترقية الزائفة لـPDF/OCR إلى trusted | إثبات رفض PDF OCR غير المؤهل، عدم إنشاء قرار مالي أو حدث اعتماد خادع؛ A1 owner |
| **PR #25 خدمات العقود** — [`reference_service.py`](https://github.com/overurdream-collab/test2/blob/8a616f7f68f506df08deccd62a9faa7d7ec89272/mcias/reference_service.py) | `write_event` مع commit للأعمال | **شرطي** | `contract_number` الذي يسمح به PR #25 يُحذف في PR #29؛ تأكيد `previous_id/version` والحدث مطلوب | نجاح إنشاء/مراجعة عقد مع صف أعمال وحدث واحد، بدون PHI؛ PR #25 + PR #29 |
| **PR #25 عقد HTTP** — [`reference_api.py`](https://github.com/overurdream-collab/test2/blob/8a616f7f68f506df08deccd62a9faa7d7ec89272/mcias/reference_api.py) | `record_outcome_independent` بعد rollback في 403/409 | **مشروط بمالك الحدث** | ازدواج 403 عند تركيب L2، حالات 409 مفصولة | طلب مباشر بحساب قراءة فقط، 403 + rollback + Audit مرة واحدة؛ تعارض 409 + Audit مجال مرة واحدة؛ PR #25 + L2 |
| **PR #25 input clauses** — [`input_clause_service.py`](https://github.com/overurdream-collab/test2/blob/8a616f7f68f506df08deccd62a9faa7d7ec89272/mcias/input_clause_service.py) | `db.add(AuditLog)` و`db.commit()` مباشرة | **ليس مستهلك API الكاتب بعد** | الترحيل قد يغير الذرية ومعنى الأحداث؛ لا ينبغي نسخ الكاتب لكل خدمة | بقاء أحداث إنشاء/تفعيل بنود المدخلات، تفرد التاريخ والأذونات؛ PR #25 + PR #29 |
| **L2 PR #28** — [`mcias/denial_events.py`](https://github.com/overurdream-collab/test2/blob/65bbddc1ae95aed22e157774f600a296a6e43926/mcias/denial_events.py) | `record_outcome_independent` بعد `get_db.rollback()` | متوافق في اختبار التركيب الجزئي السابق فقط | الكاتب PR #28 نسخة PR #25، وليس PR #29؛ لا اختبار شامل للمستهلكين جميعًا | HTTP/PG16 + Enterprise + malformed inputs + failure propagation + no double logging؛ L2 + PR #29 |

**نطاق الاستقراء:** المصفوفة تستند إلى ملفات المستهلكين التي فُحصت مباشرة وجرد PR #29 الدلالي السابق؛ لا ادعاء بأن جميع استدعاءات `AuditLog` التاريخية في النظام حُوّلت إلى الكاتب المشترك.

**أدلة تاريخية دون تعميم:** PR #28 حقق سابقًا نجاح بوابات L2/Enterprise/G1–G9 في تركيبه الضيق باستخدام كاتب PR #25؛ وتجربة Reader/PR29 على PostgreSQL 16 سجلت 36 مراجعة اصطناعية ناجحة: [Run #39462023940](https://github.com/overurdream-collab/test2/actions/runs/39462023940). لم تُشغّل نسخة مركبة تجمع كل الفروع الستة.

---

## 3 — OCR-to-A1 Evidence & Trust Contract v1

### 3.1 الهيكل المعياري المقترح

**توضيح معماري:** Shared Audit مسار توثيق ومراقبة موازٍ للتدفق؛ يمر عبره `audit_event_id` والنتيجة المعتمدة ولا يُستخدم كقناة لنقل النص الطبي أو القيم الأولية إلى A1. ينتقل سجل الدليل المقيّد من G2/Reader إلى مستهلك A1 المؤهل، فيما يثبّت Audit تاريخ قرار المراجع فقط.

اعتماد `mcias.reader.reviewed_ocr_evidence.v1` الموجود في [`reader_reviewed_ocr_contract.py`](https://github.com/overurdream-collab/test2/blob/fbac4afb34c8136681adf37aefda3975912dac4c/scripts/reader_reviewed_ocr_contract.py) بوصفه **نقطة بدء انتقال البيانات**، وليس اعتمادًا طبيًا أو مدخلًا موثوقًا تلقائيًا لـA1.

| المجموعة | الحقول والحدود |
|---|---|
| النطاق والتعيين | `schema_version`, `organization_id`, `document_id`, `job_id`, `candidate_id`, `row_id`, `field_name` |
| أصل المستند | `original_sha256` (64 hex) + مصدر G2 المشفر، وإثبات إعادة فتح الأصل والتحقق من البايتات |
| موضع الدليل | `locator.page >= 1` و`locator.bbox_pixels=(x0,y0,x1,y1)` مرتبة داخل حدود الصفحة |
| القراءة الآلية | `ocr_value`, `uncalibrated_ocr_confidence`؛ لا تعامل النسبة كثقة طبية معايرة |
| قرار النقل | `transcription_status`, `reviewed_value`, `reason_code`، حالة الرفض/عدم الحسم |
| تاريخ المراجعة | `versions[]`: `version`, `operation_id`, `event_id`, `audit_event_id`, `reviewer_user_id`, `from_state`, `to_state`, `corrected_value` |
| الثقة المسموح بها | `source_original_bytes_sha256_checked`, `g2_native_rows_verified`, `clinical_service_verified`, `tariff_verified`, `financial_eligibility_verified`, `a1_trusted_input_eligible` |
| السلطة المالية | `financial_decision = NOT_AUTHORIZED` دائمًا في عقد النقل |

المراجع وهويته ومؤسسته وصلاحياته تُستمد من Session خادمية؛ يرفض العقد تمرير هوية مزيفة من العميل. تغيير قرار سابق يكون بإصدار جديد، وليس UPDATE لمصدر OCR أو سجل المراجعة. `operation_id` يجب ألا يُعاد مع حمولة مختلفة، وإعادة الحمولة نفسها تُرجع مرجع الحدث السابق دون إدخال حدث آخر.

### 3.2 حدود الثقة غير القابلة للاختزال

| الحالة | معناها | ما **لا** تعنيه |
|---|---|---|
| `TRANSCRIPTION_ACCEPTED` / `TRANSCRIPTION_CORRECTED` | تصديق بشري على نقل نص أو تصحيحه مع مرجع الأصل | لا إثبات حصول خدمة طبية ولا صلاحية سعر ولا دفع |
| `CLINICAL_VERIFIED` | **تصديق طبي مستقل مستقبلي** من مخول وبأدلة | ليس نتيجة OCR أو تفسير النموذج بمفرده |
| `TARIFF_APPROVED` | موافقة مرجع تعاقدي ساري، وحدة/عملة/بند ومصدر عقد موثوق | ليس مجرد `ProviderTariff.amount` أو نص عقد مستخرج |
| `PAYMENT_AUTHORIZED` | جهة مالية مخولة طبقت الأهلية والسقوف والاعتمادات | لا يمكن إسنادها إلى Reader أو A1 الاستشاري |

لا تظهر حالات `CLINICAL_VERIFIED`, `TARIFF_APPROVED`, `PAYMENT_AUTHORIZED` كحقول ثقة `True` في Reader الحالي؛ هذه **مراحل سلطة مستقلة مقترحة** وليست انتقالات حالة متاحة لـReader. الحقول الخمسة المحمية في عقد Reader تظل False؛ ويظل `financial_decision=NOT_AUTHORIZED`.

**قاعدة بوابة A1:** `TRANSCRIPTION_ACCEPTED` لا ينتج `a1_trusted_input_eligible=True`، ولا يسمح للـPDF/OCR بتعيين `extracted_rows_equal_original=True` أو `original_sha256_verified=True` داخل `A1SourceVerification` دون إثبات أصلي مكافئ ومصدق من G2 ومحول A1 معتمد. يستخدم Reader التجريبي `analyze()` للحساب الاستشاري فقط. عقد A1 الموثوق الحالي يقبل CSV/XLSX عند تحقق صفوف المصدر، ويرفض مسار PDF/OCR غير المؤهل.

**حماية الخصوصية:** تفاصيل Audit تحمل IDs، نوع الحدث، إصدار المراجعة، `reason_code` معتمدًا، ولا تحمل `ocr_value` ولا `reviewed_value` ولا تشخيصًا أو اسم مريض أو SHA الأصل ضمن details. القيم الطبية والإحداثيات التفصيلية تبقى في سجل الأدلة المقيد الوصول، مع مرجع event فقط في Audit.

### 3.3 بوابات قبول انتقال الأدلة

- G2: وجود SourceFile/Document/Job لنفس المؤسسة، بايتات مشفرة قابلة لإعادة الفتح وبصمة SHA-256 صحيحة، عدم قبول cross-tenant locator.
- Reader: عرض نفس الصفحة والصندوق، مرشح OCR مستقل عن تصحيح البشر، وثوق إصدار المراجعة وهويتها ومنع تعديل التاريخ.
- Shared Audit: نجاح المراجعة وحدثها **ذريان**؛ الفشل والرفض بعد rollback مستقلان؛ عدم تسرب PHI؛ event_id يطابق سجل PostgreSQL.
- A1: نقص أدلة أصل الصفوف في PDF/OCR يؤدي إلى `HUMAN_REVIEW`/`INSUFFICIENT_EVIDENCE` لا تفويض مالي؛ تغيّر قيمة بعد تصحيح مراجع لا يبدّل الأصل المحفوظ؛ اختبار Decimal الدقيق والاستحقاق المفقود.
- طب/تعرفة/مال: اختبارات مستقلة وأصحاب اعتماد مستقلون؛ لا تمرير مباشر من OCR إلى PAYMENT_AUTHORIZED.

---

## 4 — Alembic Integration Test Plan — لا تنفيذ

أُحيل الجرد التاريخي إلى DG-001، ويُستخدم هنا **اعتماد الاختبار فقط**. الأساس المشترك `0018_claim_query_indexes`. المساران المتباعدان:

`0019_reference_points → 0020_contract_proposals` (PR #23، مع PR #22)  
`0019_input_clauses → 0020_manual_contract_metadata` (PR #25).

**خيار التصميم المفضل للمراجعة:** الالتقاء بمراجعة Alembic **جديدة ذات معرف فريد** تعتمد على كلا رأسي 0020، مع الاحتفاظ بالمراجعات التاريخية كما هي. لا نؤكد أنه الحل النهائي قبل معاينة deployment stamps والنماذج والجداول الفعلية. احتمال الحاجة إلى ترتيب تطبيق إضافي أو سكربت data migration غير مدروس ينقل القرار إلى STOP.

### 4.1 خطة التسلسل والاعتماديات

1. موافقة L1 على حارس هدف الترحيل مع قاعدة PostgreSQL16 اصطناعية وحصرية؛ تجميد SHAs وعزل بيانات الاختبار عن الإنتاج.
2. موافقة مالكي PR #23/PR #25 على القيد التاريخي وعدم حذف `reference_points`، `reference_point_closures`، `contract_proposals*`، `input_clauses*` أو `contract_versions`.
3. في **فرع جديد مصرح به لاحقًا** من `main`، تركيب الترحيلات وmetadata والنماذج الضرورية فقط؛ لا يمكن احتساب تركيب L2 PR #28 دليل توافق Alembic لأنه لا يشمل هذه الترحيلات.
4. تصميم revision التقاء جديد، والاحتفاظ بـFK `contract_proposal_promotions.reference_point_id -> reference_points.id`، وFK أحداث البنود إلى `written_authorizations.id`، وقيد `uq_contract_number_version`، وقيود الإصدار والفترة والـappend-only PostgreSQL triggers.
5. تنفيذ **اختبارات معزولة بعد تفويض مستقل** لكل من مخطط جديد، وترقية من الرأس التاريخي PR #23، وترقية من رأس PR #25، وإعادة تشغيل no-op، ومقارنة جدول alembic_version ومخطط Base.metadata.
6. اختبار تكامل الخدمات وتزامنها على **SHA مركب واحد** بعد نجاح المخطط، دون تعديل الفروع الأصلية أو تخفيض تاريخي destructive downgrade.

### 4.2 مصفوفة اختبارات PostgreSQL 16 المستقبلية

| بوابة | السيناريو | شرط النجاح |
|---|---|---|
| M-01 | `alembic history` / `heads` مع الالتقاء | شجرة سليمة ورأس نهائي واحد متفق عليه |
| M-02 | fresh-schema upgrade | إنشاء جميع الجداول والـFKs والفهارس والقيود والـtriggers المقصودة |
| M-03 | ترقية قاعدة اصطناعية من رأس PR #23 | استكمال فرع PR #25 دون إسقاط بيانات PR #23 |
| M-04 | ترقية قاعدة اصطناعية من رأس PR #25 | استكمال فرع PR #23 دون إسقاط بيانات PR #25 |
| M-05 | إعادة الترقية no-op والتحقق من `alembic_version` | ثبات التاريخ وعدم تكرار إدخالات/حذف |
| M-06 | version/FK/period negative cases | فشل cross-tenant والبيانات غير المتسقة بالقيد الصحيح |
| M-07 | immutable history negative UPDATE/DELETE | رفض تعديل المراجع والمراجعات والترقيات التاريخية |
| M-08 | Audit real writer / rollback / duplicates | نجاح حدث واحد لكل رفض وخطر UNKNOWN محجوب حتى حسمه |
| M-09 | G2 provenance → Reader → A1 | لا تغيير لعهدة الأصل ولا ترقية OCR إلى مالية |
| M-10 | G1–G9، Enterprise، عقد PR #25، Contract Intelligence PR #23 | PASS فعلي على SHA واحد، دون SKIP إلزامي أو تجاوز فشل |
| M-11 | metadata / offline SQL / constraints diff | لا خروج غير مفسر عن ORM أو DDL، ولا هدف DB غير معتمد |

لا يُستخدم `alembic stamp` لإخفاء فروع غير مطبقة، ولا `downgrade` تدميري لمحو التاريخ، ولا يعد مجرد نجاح compile أو اختلاف اسمي في `0019` سببًا لإعادة كتابة revisions الأصلية.

---

## 5 — File Ownership & Conflict Prevention Matrix

| الملفات / الطبقة | مالك القرار | ما يتطلب مراجعة قبل التركيب |
|---|---|---|
| `mcias/audit_writer.py`, `mcias/audit_contract.py` | PR #29 — Shared Audit | توحيد الأسماء والحقول، الخصوصية، عدم التكرار، إدخال المستهلكين |
| `mcias/reference_api.py`, `reference_service.py`, `input_clause_service.py`, `models_input_clauses.py` | PR #25 — Unified Inputs | إزالة ازدواج 403 دون إسقاط تسجيل 409، حماية النسخ التاريخية |
| `mcias/models_contract_proposals.py`, `models_reference_points.py`, PR23 APIs | PR #23 ومالك PR #22 المرجعي | سلامة FK وحالة مقترحات DRAFT وعدم تفعيل أثر مالي |
| `mcias/agents/a1_*`, `invoice_integrity.py` | PR #20 — A1 | Trusted CSV/XLSX v1 ورفض OCR PDF وعدم ترقية نتائج A1 إلى قرار |
| `scripts/reader*`, `document_reader_*` وواجهة المراجعة | Document Reader owner | عقد ReviewedOCREvidence، صلاحية `ingestion.review`، عدم اعتماد OCR طبيًا |
| `mcias/models_ingestion.py`, `mcias/ingestion/*`, `mcias/storage.py` | G2 owner | عهدة الأصل، SHA، source locator، تسجيل المصدر الحالي |
| `mcias/denial_events.py`, request rollback, matrix DG-003 | L2 Integration Lead | ملكية 403 واحدة، rollback، تنسيق Shared Audit ولا تعديل ملكية PR آخر |
| `mcias/app.py`, `alembic/env.py`, `alembic/versions/*` في النسخة المركبة | مالك دمج مركزي + L1 + مالكو PR23/25 | نقطة تغيير مشتركة، لا تعديلات متزامنة ولا استبدال ملفات بالجملة |
| اختبارات CI وQA المشتركة | QA integration owner | الاحتفاظ باختبارات الفروع، شرط SHA واحد، تحليل SKIP وPASS |

**آلية منع التعارض:** جدول provenance لكل ملف/blob SHA؛ مراجعة `main` وأحدث HEAD قبل إنشاء فرع؛ منع overwrite/force-reset؛ ملفات `app.py`, `alembic/env.py`, `audit_writer.py` تحتاج حلًا انتقائيًا وموافقة مالك المصدر؛ إخطار الملاك بالتغييرات المؤثرة، ثم تشغيل Gate مستقل في نسخة مؤقتة. لا تغيير فروع الملاك من قبل L2.

---

## 6 — سجل القرارات المفتوحة (Decision Register)

| ID | القرار المطلوب | مالك الاعتماد | النتيجة الافتراضية حتى القرار |
|---|---|---|---|
| D-01 | هل PR #29 canonical v1 للحفظ؟ اعتماد Event taxonomy والحقول التي قد تُحذف من PR #25 | PR #29 + PR #25 + أمن L2 | BLOCKED لإحلال الكاتب |
| D-02 | عقد `request_attempt_id`/`decision_key`، UNIQUE DB و`event_id` الثابت وتسوية UNKNOWN | PR #29 + L2 + L1/DB owner | لا Exactly-once عام |
| D-03 | جهة تسجيل 403 في `create_contract` و409 في العقود بعد دمج `get_db` | PR #25 + L2 | STOP عند ازدواج Audit |
| D-04 | تحويل G2 وInputClause من `AuditLog` المباشر إلى Writer مع الحفاظ على المصدر/الذرية | G2 + PR #25 + PR #29 | بلا ترحيل تلقائي للمستهلك |
| D-05 | صلاحيات `ingestion.review` التشغيلية، خصوصية نسخة المراجعة ويد المراجع | Document Reader + IAM/RBAC + PR #29 | التجربة فقط |
| D-06 | معيار تأهيل PDF OCR إلى G2 trusted rows ثم A1، والتحقق من كل صف وصندوق ونسخة | G2 + Reader + A1 | `a1_trusted_input_eligible=False` |
| D-07 | اعتماد تحقق الخدمة الطبية بمعزل عن النص | Medical governance owner | `clinical_service_verified=False` |
| D-08 | عقد التعرفة والتوقيع المؤسسي المرجعي الساري/وحدة الرسم | PR #23 + PR #25 + G3/contract owner | `tariff_verified=False` |
| D-09 | موافقة الدفع والأهلية بعد فحوص السياسات المستقلة | Financial authorization owner | `financial_decision=NOT_AUTHORIZED` |
| D-10 | ترحيل التقاء Alembic واختيار رأس واحد، آلية ترقية كل رأس تاريخي | L1/Alembic owner + PR #23 + PR #25 | NO MIGRATION |
| D-11 | السماح بفرع اختبار مركب مستقل وحزمة قبول API/PG16 | المشرف المركزي + L2 + QA | NO INTEGRATION BRANCH |
| D-12 | السياسة المعتمدة لتدقيق Anonymous auth failures وحفظ الحدث دون هوية مخترعة | أمن المنصة + PR #29 | غير مدعوم |

---

## 7 — قبول DG-003 وSTOP gates

### DG-003 design review acceptance

- [x] تحديث SHAs والتحقق من المصدر الفعلي لكاتب PR #25 وPR #29.
- [x] توثيق متطلبات التوافق مع المستهلكين الفعليين ومناطق `AuditLog` المباشرة.
- [x] تعريف طبقات الثقة وعقد `ReviewedOCREvidence` دون ترقية مالية.
- [x] ربط تصميم اختبار Alembic بالمراجعة DG-001 السابقة، دون تكرار جردها أو تنفيذها.
- [x] تحديد مالكي الملفات ومسؤوليات حدث HTTP/DB.
- [x] صياغة القرارات المعلقة والبوابات السلبية.
- [ ] اعتماد العقد من جميع الملاك (مرحلة مراجعة مستقلة لاحقة).
- [ ] اختبار نسخة مركبة بجميع المستهلكين والترحيلات على SHA واحد (يتطلب تفويضًا جديدًا).

### STOP gates قبل أي طلب دمج/نشر

1. تعدد رؤوس Alembic دون مسار قابل للترقية من كل رأس تاريخي، أو نقص FK/trigger/unique/check.
2. انزلاق `mcias/app.py` إلى 500 بسبب Writer غير مثبت، أو غياب ربط معاملة الأعمال/الرفض.
3. أكثر من حدث من **نفس قرار رفض HTTP** أو غياب حدث دائم عند الرفض؛ أو دمج طلبَي HTTP مستقلين في حدث واحد.
4. غياب تسوية UNKNOWN، أو الادعاء بزواله عبر إعادة `commit()` غير آمنة.
5. تهريب PHI/أسرار/قيم OCR أو معرف مصدر حساس إلى `AuditLog.details`، أو فقد required provenance في سجل المصدر.
6. استخدام Actor من client payload، عدم فحص RBAC/organization_id، أو تمكين anonymous writer دون سياسة.
7. تحويل `TRANSCRIPTION_ACCEPTED` إلى `clinical_service_verified=True` أو `tariff_verified=True` أو `PAYMENT_AUTHORIZED`.
8. اعتبار PDF/OCR مصدر A1 موثوقًا دون G2 native original row reconciliation واعتماد المحول.
9. إسقاط اختبار أمني تاريخي أو احتساب SKIP إلزامي PASS أو تجميع نتائج CI من SHAs مختلفة.
10. إدخال ترحيلات/واجهة/عقود غير لازمة أو استخدام بيانات إنتاجية بلا تفويض.

**نقطة الاستئناف:** مراجعة D-01/D-03 أولًا مع PR #29 وPR #25 وL2، ثم D-02 مع L1، وD-05/D-06 مع Reader/G2/A1، وD-10 أخيرًا بعد اعتماد المخططات. بعد التوقيعات يمكن **طلب** تفويض إنشاء فرع معزول؛ لا تمنحه وثيقة DG-003 نفسها.

**الحكم:** `DG-003 DESIGN READY FOR INDEPENDENT REVIEW`، ولا يساوي `INTEGRATION PASS` أو إذنًا بتشغيل ترحيلات أو دمج أو نشر.


## 8 — DG-003 Independent Review Handoff (20 أكتوبر 2026)

**نطاق هذا التحديث:** توثيق وتسليم ومراجعة عقود فقط؛ لا تغيير في الكاتب أو الترحيلات أو فروع التشغيل. SHAs أعلاه فُحصت مجددًا؛ تغيّر HEAD فرع Document Reader فقط مقارنة بمرجع إعداد التقرير، ولم يُعَد تقييم أثر هذا التغيير على العقد، لذلك يلزم من مالكه مراجعة الفرق قبل الاعتماد.

| القرار | المالك المسؤول | الدليل المطلوب للتوقيع | معيار القبول | الحالة |
|---|---|---|---|---|
| DR-01: Event taxonomy والتحقق | مالك PR #29 + أمن L2 | مقارنة أحداث PR #25/G2/Reader وعينات قيم مرفوضة/مسموحة على التنفيذ الأصلي | كل اسم وسبب ونوع مورد معروف، لا إسقاط صامت لحقل تدقيق مطلوب، ولا PHI | **PROPOSED — OWNER REVIEW PENDING** |
| DR-02: توافق المستهلكين و403/409 | مالك PR #25 + L2 | مخطط مالك الحدث لكل endpoint، واختبار HTTP PostgreSQL من تركيب مأذون لاحقًا | حدث واحد لكل رفض 403، و409 مرة واحدة، ولا تغيير أعمال بعد rollback، ومحاولتان مستقلتان = حدثان | **PROPOSED — OWNER REVIEW PENDING** |
| DR-03: منع التكرار والتسوية | مالك PR #29 + L2 + L1 | تصميم attempt_id/decision_key، UNIQUE/مكافئ، وفشل commit غير المؤكد | لا ازدواج عند إعادة المحاولة أو السباق، ولا ادعاء نجاح عند UNKNOWN | **PROPOSED — OWNER REVIEW PENDING** |
| DR-04: توافق Alembic | L1 مع PR #23 وPR #25 | مراجعة graph التاريخي، FK/constraints/triggers، وخطة upgrade من كل رأس | لا حذف أو تعديل ترحيلات مطبقة، وتنجح خطة PostgreSQL 16 المعزولة بعد التفويض | **PROPOSED — OWNER REVIEW PENDING** |
| DR-05: حدود OCR | مالك Document Reader + G2 + A1 | مراجعة أحدث Reader HEAD وعقد reviewed_ocr_evidence وسلسلة SHA/bbox/version/audit | قبول النقل لا يمنح تصديقًا طبيًا/ماليًا أو a1_trusted_input | **PROPOSED — OWNER REVIEW PENDING** |
| DR-06: G2/InputClause direct Audit | G2 + PR #25 + PR #29 | جرد الاستدعاءات المباشرة وخطة حفظ التاريخ والتوافق | ذرية معاملة النجاح وعزل المؤسسة وعدم فقد حقول provenance | **PROPOSED — OWNER REVIEW PENDING** |

**المعتمد سابقًا:** السماح بإعداد التصميم وتسليمه فقط؛ PR #29 مرشح مرجعي، وليس عقدًا معتمدًا. لا يوجد في هذه الوثيقة توقيع اعتماد من ملاك PR #29 أو PR #25 أو L1 أو Reader أو A1. نجاح CI التاريخي لا يساوي اعتمادهم.

**BLOCKERS:** DR-01 إلى DR-06 غير معتمدة، منع التكرار الدائم غير مثبت، خطر ازدواج 403/409 غير مغلق على تركيب شامل، Alembic متعدد الرؤوس لم يختبر على تطبيق موحد، حدود OCR/A1 تحتاج موافقة أصحابها، وتغيّر HEAD Reader بعد إعداد التقرير.

**حالة التسليم:** `DG-003 DOCUMENTED — OWNER REVIEW PENDING`. لا إذن بفرع تكامل أو merge أو deploy.