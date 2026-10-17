# مصفوفة القبول والاستلام A1 — معالجة المراجعة المستقلة
**التاريخ:** 2026-10-17 | **الحالة:** READY_FOR_INDEPENDENT_REVIEW, NOT PRODUCTION | **Branch:** feat/mcias-a1-invoice-integrity | PR #20 Draft.

| البند | الحالة الدقيقة | مصدر الإثبات / العائق |
|---|---|---|
| Research First / Reuse Before Build | RESEARCH_DOCUMENTED | docs/agents/A1_OPEN_SOURCE_RESEARCH_AR.md |
| A1 Decimal deterministic and Qwen3-8B true AI | TESTED_SYNTHETIC (قبل تكامل P0) | Actions run 39055788148؛ لا benchmark مستقل جديد |
| Trusted G2/G4 CSV/XLSX original-byte adapter | VERIFIED_SYNTHETIC | mcias/agents/a1_trusted_input.py؛ reparse G2, storage.get, sha256, row matching |
| Pydantic strict schema / no NaN / tenant and currency | VERIFIED_SYNTHETIC | A1Input وtests/test_a1_trusted_input.py |
| G4 normalized claim amount / date / provider / beneficiary original match | VERIFIED_SYNTHETIC | G4 claim_normalization + corruption test |
| G3 H1 old 5000, new 5500, H2 7000 | VERIFIED_SYNTHETIC_DIAGNOSTIC | half-open approved contracts; ProviderTariff lacks unit |
| G3 signed approved per-unit price + G5 policy fingerprint | BLOCKED_EXTERNAL_APPROVAL | no invented quantity / unit, no signed policy grant in adapter |
| Contract Intelligence and ReferencePoint PR22/PR23 | NOT_MERGED | Draft PR #22 and #23; diagnostics not financial authority |
| Palermo actual source bytes and row equality | VERIFIED_SYNTHETIC | EncryptedStore SHA-256 and reparse original |
| Palermo independent clinical performance and model quote attestation | NOT_DONE | hospital signed records/semantic source verification absent |
| A1 internal same-source invoice row duplication | TESTED_SYNTHETIC_ADVISORY | potential duplicate REVIEW only, no calculated savings |
| A1 read-only HTTP preview | TESTED_SYNTHETIC | disabled by default, prohibited in production, protected by bearer/RBAC/no-store |
| G6/G7 provisional review_packet and four-way code | INTERFACE_ONLY | only HUMAN_REVIEW/MISSING_ATTACHMENTS; no final approval or G7 realized savings |
| G8/Enterprise and G9 regression | VERIFY_EXACT_SHA | CI links below |
| Independent clinician-labelled new blind gold, Arabic/English OCR PDF | NOT_DONE | cannot infer clinical accuracy from curated 36-case retest |
| Institution signed acceptance, production deployment, main merge | BLOCKED_BY_APPROVAL | explicitly prohibited in current assignment |

## روابط الإثبات على Commit 0962b54a896c572fc8db9d74d6d33cb044d25601
- G1–G7 PostgreSQL, unit and dependency audit PASS: https://github.com/overurdream-collab/test2/actions/runs/39065243710
- G9 security/recovery PASS: https://github.com/overurdream-collab/test2/actions/runs/39065243812
- Documentation traceability PASS: https://github.com/overurdream-collab/test2/actions/runs/39065243702
- Browser/Enterprise: https://github.com/overurdream-collab/test2/actions/runs/39065243743 (راجع الحالة الحقيقية)
- Qwen3-8B: https://github.com/overurdream-collab/test2/actions/runs/39065243840 (راجع الحالة الحقيقية)
- Reviewer P0/P1 findings: https://github.com/overurdream-collab/test2/pull/20#issuecomment-6239159233
- Earlier model false-positive evidence FP2: https://github.com/overurdream-collab/test2/actions/runs/39051176994

## DG-001: ارتباط لا إعادة كتابة مصادر الحقيقة
PR #22 (https://github.com/overurdream-collab/test2/pull/22) يحدد DG-001 وCURRENT_STATE وEXECUTION_JOURNAL وACCEPTANCE_MATRIX وCODEX_EXECUTION_HANDOFF؛ هذه الملفات *ليست مدمجة في فرع A1*. لا تكتب نسخة تناقضها أو تدعي قبولها. عند اعتماد PRs احفظ أحداث A1 الجديدة ومصادر CI في الفهارس المعتمدة مع روابط، دون محو السجل A1 التاريخي. ملف STATE_A1.json مجرد snapshot ويجب مقارنة آخر SHA/CI عند كل استلام.

## الترتيب الحرج للتسليم
1. فحص HEAD وCI الحالية وتوثيق أي فشل أو إلغاء.
2. موافقة مصدر معتمد على وحدة الفوترة، السياسة المالية الموقعة وربط G3/G5.
3. Palermo مستقل يؤكد bytes/quote/clinical attestation؛ لا يكفي وجود النص أو علم attested مقدم من جهة غير مصادَق عليها.
4. Golden blind مستقلة من مراجعي فواتير مستقلين على PDF/OCR عربي/إنجليزي وبنود كثيرة؛ احسب TP/FP/FN/TN والموارد.
5. بعد تقنين PR22/23، اكمل G5 المالي المعتمد وG6 قرار المراجع وG7 التقرير ثم UAT؛ لا دمج أو نشر دون موافقة صريحة.
