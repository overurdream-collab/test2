# DG-001 — Document Reader: G2 → Shared Audit → A1 Integration Readiness

**النطاق:** عقد واختبار تكامل معزول ببيانات اصطناعية فقط؛ لا دمج ولا نشر ولا ترحيلات أو تعديل فروع المرجع.

## إصدارات المصدر المرجعية — تثبيت قابل لإعادة التحقق

| المكون | SHA عند الفحص | الوضع |
|---|---|---|
| Document Reader | `5d32b8290c0d691cfc9e8ad8741ef6faf6ec3bb9` قبل التجربة | Human Review Pilot SUCCESS على Run #39405041831 |
| A1 PR #20 | `b536a94adf4d190ac48856bd435a8a624f3931f4` | Draft غير مدمج؛ `mcias.a1.input.v1` يرفض PDF/OCR |
| Shared Audit PR #29 | `fd1bb1d22f1957f40688baa207cdf449b0690cd9` | Draft غير مقبول تشغيليًا؛ أصل `mcias/audit_writer.py` و`mcias/audit_contract.py` مستخدمان قراءة فقط |

مكونات G2: `EncryptedStore`، `IngestionDocument`، `IngestionJob`، `SourceFile`، و`Candidate` الاصطناعي الوارد من الاختبارات السابقة. لا إعادة اختبارات G2/Chromium السابقة من الصفر.

## العقد الرسمي التجريبي

المصدر البرمجي: `scripts/reader_reviewed_ocr_contract.py`.

`mcias.reader.reviewed_ocr_evidence.v1` يسجل: `organization_id`، `document_id`، `job_id`، `candidate_id`، `original_sha256`، `row_id`، `field_name`، `page`، `bbox_pixels`، `ocr_value`، `reviewed_value`، `uncalibrated_ocr_confidence`، `transcription_status`، إصدارات المراجعة مع `operation_id` و`reviewer_user_id` و`audit_event_id` لكل إصدار، وتحقيق الأصل. يرفض حقولًا إضافية وإصدارات انتقال متناقضة، ويمنع حالة TRUSTED العامة.

**الفصل بين سلطات الاعتماد:** صحة نقل النص `TRANSCRIPTION_ACCEPTED/CORRECTED` تعني أن مراجعًا مخوّلًا قال إن النص منقول؛ لا تثبت أن الخدمة الطبية نُفذت، ولا أن وحدة التعرفة صحيحة، ولا استحقاق الدفع. حقول `g2_native_rows_verified` و`clinical_service_verified` و`tariff_verified` و`financial_eligibility_verified` و`a1_trusted_input_eligible` مثبتة جميعها على `false` في هذا العقد. `financial_decision=NOT_AUTHORIZED`.

## أصغر محول اختبار PostgreSQL 16

المصدر: `scripts/reader_g2_audit_a1_pg16_contract.py`. التنفيذ على DB `mcias_reader_contract` في `127.0.0.1` فقط، مع متغير موافقة `MCIAS_READER_PG16_ISOLATED=YES`، والتأكد أن الجداول المختبرة غير موجودة قبل الاختبار. مخزن AES-GCM مؤقت، وعينات PDF صناعية، واستخراج OCR مطبق على بايتات PDF المسترجعة.

الاختبار ينشئ جدول مراجعات **مجال العمل** `reader_review_version_test_only` داخل DB المؤقتة فحسب، وليس سجلاً موازيًا لـAudit؛ كل قرار ناجح يستدعي `write_event()` الأصلي من PR #29 **في نفس معاملة** إدراج الإصدار. رفض الصلاحيات المُشتق من حساب صالح يُسجل بـ`record_outcome_independent()` بعد التراجع، وفق إرشادات PR #29. حقول Audit محدودة ضمن `clean_details`: لا نصوص طبية، ولا مبالغ، ولا SHA للأصل في Audit. مراجع الأحداث تعود إلى سجل Audit الفعلي نفسه.

هوية المراجع مشتقة من `SessionToken` الخادمي مع التحقق من صلاحية الجلسة ومؤسسة `User` وحالة `active` وRBAC عبر `has_permission('ingestion.review')` بعد منح تجريبي محلي؛ لا يوجد تفويض تشغيلي لهذه الصلاحية في الفروع الأصلية. `Decision` يقبل `candidate_id,expected_version,operation_id,action,corrected_value,reason_code` فقط، ويمنع حقول reviewer/org من العميل.

على PostgreSQL: `SELECT ... FOR UPDATE` على `IngestionDocument` يجمع الإصدارات المتزامنة؛ `UNIQUE(candidate_id,version)` و`UNIQUE(candidate_id,operation_id)` تمنع السباق والتكرار، وإعادة إرسال نفس العملية تتلقى معرف Audit نفسه دون إنشاء حدث إضافي. تمنع triggers التجريبية UPDATE/DELETE للمرشحات وإصدارات مراجعتها؛ ليست ترحيلات إنتاجية ولا ضمانًا ضد PostgreSQL superuser.

بعد نجاح مراجعة كافة البنود، يُحوّل `reviewed_value` إلى `a1_payload` الاصطناعي للاستشارة باستدعاء `analyze()` الأصلية من PR #20، ولا يدخل `build_a1_snapshot` أو `a1_trusted_input`؛ التحقق الرسمي لـPDF غير متوفر.

## فحوص سلبية إلزامية

- بصمة PDF خاطئة أو أصل AES-GCM معدّل.
- تغيير OCR candidate أو نسخة القرار السابقة مباشرة عبر SQL.
- انتحال هوية/مؤسسة في حقول الطلب، ومراجع دون دور، وعبور مؤسستين.
- عملية اعتماد مكررة `operation_id` (استرداد Idempotent دون إدراج Audit آخر) أو تكرار معرف العملية بحمولة مختلفة.
- طلبان متزامنان على إصدار واحد؛ ينجح أحدهما ويرفض الثاني.
- عدم اعتماد جميع الحقول يمنع المعاينة؛ تصحيح السعر بإصدار جديد ينقح **حساب A1 الاستشاري** فقط، ولا يمحو نص OCR أو مراجعاته السابقة.
- عقد A1 الموثوق لا يقبل مصدر PDF `review_required` حتى مع توافق الحقول.

## نتيجة التنفيذ وموانع النشر

**النتائج الفعلية مثبتة فقط من السجلات المرتبطة بأحدث SHA** عبر `.github/workflows/document-reader-shared-audit-pg16.yml`. لا يُعد غياب أو فشل التشغيل نجاحًا. احتفظ بكل فشل وسببه.

**موانع التشغيل اللاحقة:** PR29 لا يدعم بعد Idempotency كضمان في الخدمة نفسها، كما أن تفاصيل `AuditLog` محمية في writer لكن لا يوجد عقد استهلاك تشغيلي معتمد ولا تناغم مضمون مع صلاحيات Shared Audit المتعددة. يجب حسم مالك معاملة HTTP والرفض بعد Rollback ومنع ازدواج الأحداث في النظام المشترك. `ingestion.review` منح اختباري غير مثبت كدور إنتاجي. عقد A1 الموثوق لا يدعم PDF ولا يجيز `extracted_rows_equal_original=True` من قبول نقل النص، والتوافق مع G4 والمرجع المتعاقد عليه لم يثبت؛ لا تفويض مالي أو طبي.

**HANDOFF:** لا تدمج أو تنشر. لا تغيّر PR #20 أو #29 أو main. القرار النهائي مشروط بأدلة CI الفعلية، ولا يتعدى مسار الاستشارة المعزولة.

## Final PG16 evidence and HANDOFF — 2026-10-20

**Validated code SHA:** `9552f494e3ca2e8b490771b8b719034b519f3755`. GitHub Actions [Run #39462023940](https://github.com/overurdream-collab/test2/actions/runs/39462023940): **SUCCESS** on the exact code SHA. Job `pg16-isolated-readiness`: SUCCESS, PostgreSQL service `postgres:16` disposable DB `mcias_reader_contract`, original SHA-pinned PR20 and PR29 checkouts; no merge/deploy. Artifact `reader-pg16-g2-shared-audit-a1-contract` (Artifact ID `12283277323`) contains original synthetic PDFs, exact exported reviewed OCR contract sample, `pg16_readiness_evidence.json` and source proofs. Workflow also printed `PINNED_A1_TRUSTED_PDF_REJECTION_PASSED`.

**Measured:** two synthetic PDF invoices; 36 OCR cell fields reviewed and paired with 36 actual PR29 Shared Audit `success` events in PostgreSQL (one event per accepted field). Version records contain the actual shared event IDs, and role+session+tenant are derived server-side. Concurrent submissions on the same expected version: one succeeds, one fails. Idempotent retransmission returns the original event rather than double writing. Decimal arithmetic advisory from unchanged A1 yields 0 mismatches for valid invoice, 2 for exchanged totals and 1 after a separately versioned synthetic price correction. Every such result remains `HUMAN_REVIEW` and `financial_decision=NOT_AUTHORIZED`.

**Negative gates demonstrated (13):** FAKE_CLIENT_ACTOR, UNGRANTED_REVIEW_PERMISSION, CROSS_ORGANIZATION, ORIGINAL_DIGEST_TAMPERED, CONCURRENT_VERSION_CONFLICT, IDEMPOTENT_DUPLICATE, OPERATION_PAYLOAD_REUSE, ENCRYPTED_ORIGINAL_TAMPERED, DIRECT_REVIEW_HISTORY_MUTATION, DIRECT_SOURCE_CANDIDATE_TAMPER, MISSING_PRICE_REVIEW_HOLDS_A1, ORIGINAL_SHARED_AUDIT_INDEPENDENT_DENIAL, NON_NUMERIC_PRICE_CORRECTION. PostgreSQL reports two `TEST_APPEND_ONLY` errors **expected by intentional negative UPDATE tests**, not CI failures. `record_outcome_independent()` logged the denied cross-tenant action under the **foreign actor's own tenant** after rollback; no source hash, patient text or amount appeared in the Audit event details.

**Original-source boundary still closed:** `a1_trusted_input` from PR20 explicitly rejects the scanned PDF in `review_required`, so no `extracted_rows_equal_original=True` or `original_sha256_verified=True` is asserted in an A1 trusted snapshot. `ReviewedOCREvidence` remains a review-transcription representation, not approved medical performance or tariff/payment authority. The bridge uses `analyze()` for arithmetic diagnostic only. PR29 original writer has no native deduplication/version lock: these guarantees are **consumer-side synthetic PG16 constraints**, not a PR29 feature or proof of operational readiness.

**Acceptance recommendation:** `PARTIAL — SPECIFIC GAPS` for production integration readiness. The *isolated transaction and contract* are technically verified and reproducible, but A1 PDF trusted adapter compatibility, human clinical verification, integration with operational role/permissions, PR29 approval, durable Shared Audit consumer ownership and centrally agreed event vocabulary are not established. No operational integrations or schema changes authorized.

**Next approved work requires independent decision:** (1) centrally approve OCR transcription-only source contract and tenant-scoped review RBAC (distinct from medical service signoff); (2) certify Shared Audit writer+HTTP rollback ownership/deduplication by PR29's own gates, not Reader tests; (3) implement and approve trusted G2 original row/box reconciliation for PDF/OCR, signed human attestation and traceable G4 linkage before evolving A1's trusted adapter; (4) independent clinical, tariff and financial policy approvals before any payer action.

