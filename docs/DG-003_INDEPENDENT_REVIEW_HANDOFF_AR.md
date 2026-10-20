# MCIAS v2.0 — DG-003 Independent Review Handoff

**الحالة:** DG-003 DOCUMENTED — OWNER REVIEW PENDING  
**النطاق:** Documentation and owner coordination only. NO MIGRATION / MERGE / DEPLOY.  
**الوثيقة الكاملة الأصلية:** [DG-003 — Shared Integration Contract & Readiness](./DG-003_SHARED_INTEGRATION_CONTRACT_READINESS_AR.md) — محفوظة كاملة دون اختصار في فرع التوثيق (285 سطرًا). هذه المذكرة مجرد تسليم ومصفوفة قرارات، وليست بديلًا عن التقرير الكامل.

## المراجع المثبتة بتاريخ 2026-10-20

| المكون | SHA |
|---|---|
| main | b69defa2f621458ef44d790b510840307a81009a |
| PR20 | 6af41a04cf887d389656c9ce7ffc4e03b396b5a4 |
| PR23 | 16cc288e8c71eeb5731f36fe39a16e617e6f3483 |
| PR25 | 8a616f7f68f506df08deccd62a9faa7d7ec89272 |
| PR29 | fd1bb1d22f1957f40688baa207cdf449b0690cd9 |
| Document Reader | 36e03751d71306f33ee50ce4e0dea879e2a4b3c2 |

## مصفوفة القرارات — كلها مقترحة ولم تُعتمد من الملاك

| القرار | المالك | الدليل المطلوب | معيار القبول | الحالة |
|---|---|---|---|---|
| DR-01: Event taxonomy وvalidation | PR29 + أمن L2 | اختبار أسماء أحداث PR25/G2/Reader والحقول المقبولة والمرفوضة | لا فقد حقول لازمة ولا تسرب PHI؛ توافق صريح | REVIEW PENDING |
| DR-02: 403/409 ownership | PR25 + L2 | مخطط كل endpoint واختبار HTTP/PostgreSQL | rollback، حدث واحد للطلب، ومحاولتان = حدثان | REVIEW PENDING |
| DR-03: dedup وUNKNOWN | PR29 + L2 + L1 | تصميم attempt_id/decision_key وقيد دائم واختبار سباق | لا تكرار ولا ادعاء حفظ غير مؤكد | REVIEW PENDING |
| DR-04: Alembic history | L1 + PR23 + PR25 | مراجعة heads/FK/constraints/upgrade paths | لا تعديل تاريخ مطبق؛ خطة PG16 قابلة للاختبار | REVIEW PENDING |
| DR-05: OCR evidence and trust | Document Reader + G2 + A1 | reviewed_ocr_evidence.v1 وبصمة الأصل ونسخ المراجعة وأحدث Reader HEAD | TRANSCRIPTION_ACCEPTED لا يمنح CLINICAL_VERIFIED أو TARIFF_APPROVED أو PAYMENT_AUTHORIZED ولا a1_trusted_input | REVIEW PENDING |
| DR-06: direct AuditLog consumers | G2 + PR25 + PR29 | جرد G2/input_clause_service وخطة ترحيل النداءات | ذرية وtenant isolation وعدم ضياع التاريخ | REVIEW PENDING |

## الوقائع المثبتة مقابل المقترحات

- **مثبت بالمصدر:** PR25 وPR29 لهما توقيعا write_event وrecord_outcome_independent نفسيهما، لكن PR29 أشد تحققًا ويزيل contract_number من تفاصيل Audit.
- **مثبت بالمصدر:** G2 وinput_clause_service يكتبان AuditLog مباشرة؛ PR25 reference_api يكتب رفضًا مستقلًا؛ توجد مخاطرة ازدواج عند تركيب L2.
- **غير معتمد:** اختيار PR29 بديلًا تشغيليًا؛ قيد idempotency دائم؛ توحيد ترحيلات Alembic؛ تأهيل PDF/OCR كمصدر A1 موثوق.
- **أدلة تاريخية فقط:** https://github.com/overurdream-collab/test2/actions/runs/39308256438 وhttps://github.com/overurdream-collab/test2/actions/runs/39462023940. لا تثبت تركيب أحدث الفروع معًا.

## BLOCKERS

1. اعتماد قاموس الأحداث والتحقق من PR29.
2. إثبات ملكية تسجيل 403/409 وعدم الازدواج.
3. تصميم idempotency دائم وتسوية UNKNOWN.
4. اعتماد خطة Alembic مع المحافظة على تاريخ PR23/PR25.
5. اعتماد فصل OCR عن التصديق الطبي والتعرفة والصرف، ومراجعة أحدث Reader SHA.
6. مراجعة المستهلكين المباشرين لـAuditLog.

**لا توجد موافقة موثقة من أصحاب المكونات حتى الآن.**