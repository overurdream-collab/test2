# A1 — E4 source/evidence bridge — synthetic isolated continuation

### EVENT-20261021-405-01 — استلام النطاق وفحص نقطة الاستئناف
- event_id: EVENT-20261021-405-01
- when_utc: 2026-10-21T15:26:34Z (وقت التحقق؛ أوقات القراءات السابقة الدقيقة لم تسجل)
- actor: Codex / A1 owner agent
- action: READ
- reason: استكمال تفويض المشرف في worktree القائم دون تكرار العمل أو تغيير ملفات مالك آخر.
- scope: PR20 detached / A1 E4 / synthetic only؛ before HEAD وحالة الملفات تحققا مباشرة.
- before_sha: 6af41a04cf887d389656c9ce7ffc4e03b396b5a4
- after_ref: SELF
- files_or_sources: AGENTS.md؛ docs/engineering/TRACEABILITY_POLICY_AR.md؛ docs/engineering/INDEX.md؛ docs/engineering/HANDOFF_A1_AR.md؛ docs/engineering/worklogs/A1_2026-10-17.md؛ docs/engineering/worklogs/_TEMPLATE.md؛ docs/engineering/STATE_A1.json؛ scripts/check_traceability.py؛ docs/agents/A1_INVOICE_INTEGRITY.md؛ docs/agents/A1_EVIDENCE_REPORT_20261017.md؛ mcias/agents/a1_trusted_input.py؛ mcias/agents/a1_review_packet.py؛ mcias/agents/a1_fee_reference_contract.py؛ tests/test_a1_itemized_decimal_provenance.py؛ tests/test_a1* (بحث).
- command_or_method: git rev-parse HEAD؛ git status --short؛ cat/sed/tail/wc/rg؛ قراءة تعليمات المشرف وReader بالتنسيق الداخلي. المخرجات الطويلة الأولى مقطوعة؛ لا تدعي هذه القراءة اكتمال الاطلاع على كل سطر من السجل التاريخي. بحث /workspace/test2 عن mcias/agents وmcias/rules.py أعاد exit2 لعدم وجود هذين المسارين؛ لا استنتاج من نتائج البحث الغائبة.
- expected: تحديد adapter القائم وحدود الملكية وعائق يمكن إغلاقه بأصغر تغيير.
- outcome: PARTIAL
- validation: HEAD=6af41a04cf887d389656c9ce7ffc4e03b396b5a4 وحالة العمل نظيفة قبل إنشاء هذا السجل؛ الاختبارات NOT_RUN حتى الآن.
- evidence: عائق موثق وموجود بالشيفرة: unit_price فارغ يمر بتكوين items ثم يوقف A1Input Validation قبل إنتاج review_packet؛ tests/test_a1_itemized_decimal_provenance.py يثبت توقع الحجب الحالي ويصف triage gap. G3 التاريخي تشخيص فقط وليس سلطة سعر وحدة.
- risk_and_security: بيانات اصطناعية فقط؛ لا تنفيذ نموذج أو خدمة مدفوعة أو PHI؛ لا migrations؛ لا رفع OCR مرشح إلى دليل مؤهل؛ لا تغيير مالي أو G5/G3/Shared Audit/G7.
- rollback: حذف السجل غير الملتزم أو revert ذري لاحقاً؛ لا reset/merge/force push/deployment.
- next: فحص عقد integrated source الفعلي ثم إرسال اقتراح interface إلى المشرف والمستهلك قبل تعديل العقد المشترك.
- decision_status: IN_PROGRESS

### EVENT-20261021-405-02 — تنسيق عقد المصدر مع G5 وReader
- event_id: EVENT-20261021-405-02
- when_utc: not independently verifiable
- actor: Codex / A1 owner agent
- action: READ / DECISION
- reason: مقارنة bridge القديم بمصدر PR34 الفعلي وتجنب تعارض الوكلاء أو منح سلطة مالية لمرشح OCR.
- scope: A1 producer؛ G5 consumer؛ Reader anchors مرشحة فقط؛ read-only /workspace/test2.
- before_sha: 6af41a04cf887d389656c9ce7ffc4e03b396b5a4
- after_ref: SELF
- files_or_sources: mcias/agents/invoice_integrity.py؛ mcias/ingestion/parsers/csv_parser.py؛ mcias/ingestion/parsers/excel_parser.py؛ tests/test_a1_trusted_input.py؛ /workspace/test2/mcias/claim_batches.py؛ /workspace/test2/mcias/models_claims.py؛ /workspace/test2/mcias/reference_service.py؛ /workspace/test2/mcias/audit_service.py؛ /workspace/test2/mcias/audit_engine.py؛ رسائل التنسيق مع المشرف وintegration_rules وresume_reader.
- command_or_method: rg/sed/cat؛ عقد إضافي داخل review.v1 أرسل للمشرف وG5 قبل التعديل؛ قبول المستهلك مسجل في المحادثة؛ اعتماد المشرف ما زال منتظراً عند تسجيل الحدث.
- expected: مصدر قابل للاستهلاك يحتفظ بالصف والحقول دون مساواة متعجلة بين مصدر مؤهل ومخالفة مثبتة.
- outcome: PARTIAL
- validation: NOT_RUN؛ native claim locator يضيف metadata بينما A1 القديم يقارن كامل dict؛ هذا عائق شيفرة مثبت، ويجب التحقق من lineage عبر source_scope القائم لا حذف metadata.
- evidence: توافق G5 على source_evidence مع original quantity/unit_price/line_total، field_sources، claim/source_record/SHA ومعلومات scope؛ لا صلاحية من RULE_ENGINE وحده؛ Reader لا يعدل A1 ويحتفظ UNATTESTED_OCR_CANDIDATE.
- risk_and_security: لا مرجع ProviderTariff.amount كسعر وحدة؛ لا اشتقاق invoice_total أو unit_price من claimed_amount؛ لا حالات G5 موازية؛ غياب سياق خصم/ضريبة/تقريب أو قاعدة معتمدة يبقي arithmetic_qualification غير مكتمل.
- rollback: revert ذري في ملفات A1 فقط؛ لا migration أو reset أو merge.
- next: اعتماد المشرف ثم adapter/packet إضافي متوافق خلفياً، واختبارات وحدة اصطناعية مع بقاء PG16 للمالك المشرف.
- decision_status: IN_PROGRESS

### EVENT-20261021-405-03 — تنفيذ عقد E4 المتوافق وحجب الفشل إلى مراجعة
- event_id: EVENT-20261021-405-03
- when_utc: not independently verifiable
- actor: Codex / A1 owner agent
- action: WRITE / FIX / TEST
- reason: اعتماد المشرف الصريح للعقد الإضافي بعد موافقة مستهلك G5؛ إغلاق عائقي lineage وmissing-price دون إعادة بناء المكونات.
- scope: A1 owned adapter/packet/tests فقط؛ parent6af41a0 + working tree هذه الدورة؛ synthetic.
- before_sha: 6af41a04cf887d389656c9ce7ffc4e03b396b5a4
- after_ref: SELF
- files_or_sources: mcias/agents/a1_trusted_input.py؛ mcias/agents/a1_review_packet.py؛ tests/test_a1_itemized_decimal_provenance.py؛ tests/test_a1_native_source_evidence.py؛ محادثة اعتماد المشرف وتنسيق integration_rules؛ tests/test_a1_trusted_input.py (baseline/read).
- command_or_method: apply_patch؛ /workspace/security-venv/bin/python -m pytest -q tests/test_a1_trusted_input.py tests/test_a1_itemized_decimal_provenance.py (قبل التعديل)؛ focused test command أضيف إليه tests/test_a1_native_source_evidence.py بعد التعديل.
- expected: تحقق مستقل من original bytes/G2 record/G4 scope؛ original field pointers؛ no derived price؛ safe review for incomplete numeric row؛ لا analysis داخل source rebuild.
- outcome: PARTIAL
- validation: baseline قبل التعديل 19 PASS في5.23s؛ الاختبارات بعد التعديل قيد التشغيل عند تسجيل الحدث وليست PASS مفترضة. ملف test_a1_review_packet.py غير موجود، فبحثه أعادexit2؛ استخدم اختبارات adapter/contract الفعلية.
- evidence: source_evidence additive داخل review.v1، source_evidence_fingerprint checksum مستقل، full native metadata عبر existing source_scope بما يشمل eligible/excluded وCLAIMS؛ normalized original fields ثابتة؛ Line.model_validate قبل اعتماد items يحول numeric incomplete إلى invalid_invoice_row. النسخ المنفصل يمنع تعديل preview من تبديل packet بالمرجع نفسه.
- risk_and_security: qualified=false دائماً حتى explicit_adjustment_context وapproved_arithmetic_rule؛ unit_price_authority=NOT_ESTABLISHED؛ مصدر bytes لا يكفي لحكم مالي؛ native gate unit tests تستخدم verifier stub صريحاً ولا تعني PG16 INTEGRATION VERIFIED. OCR لا يدخل هذا adapter، وProviderTariff.amount تشخيص فقط. checksum ليس توقيعاً أو تصديقاً.
- rollback: revert ذري لهذه الدورة وlog المرافق فقط؛ no reset/force push/merge/deploy.
- next: اقرأ النتيجة الفعلية للاختبارات، أصلح أي فشل ثم handoff405 وحفظ commit؛ المشرف يختبر source_scope الحقيقي على PG16 وينشرDraft الحالي.
- decision_status: IN_PROGRESS

### EVENT-20261021-405-04 — نتائج الوحدة ومنع استدلال غير مفوض وتعليق regression
- event_id: EVENT-20261021-405-04
- when_utc: 2026-10-21T20:53:50Z (وقت التحقق المتاح؛ توقيت بدء الأوامر غير محفوظ)
- actor: Codex / A1 owner agent؛ المشرف لتجربة PG16 المنفصلة
- action: TEST / WRITE / HANDOFF
- reason: إغلاق الوحدة المصرح بها فقط؛ توسعة ملكية المشرف المحددة للـworkflow لمنع إعادة Qwen3-8B غير اللازمة، وحفظ أول فشل بيئة دون تعديل الاختبارات.
- scope: A1 source files ثابتة منذ manifest؛ workflow محدد ووثائق المالك؛ parent6af41a0 + working tree؛ synthetic only.
- before_sha: 6af41a04cf887d389656c9ce7ffc4e03b396b5a4
- after_ref: SELF
- files_or_sources: .github/workflows/a1-invoice-integrity.yml؛ docs/E4_A1_BRIDGE_AR.md؛ docs/engineering/HANDOFF_A1_AR.md؛ docs/engineering/INDEX.md؛ tests/test_a1*.py؛ tests/test_traceability.py؛ scripts/check_traceability.py؛ mcias/app.py؛ mcias/config.py؛ mcias/rate_limits.py؛ tests/conftest.py؛ /workspace/test2/.e2e-output/A1_G5_NATIVE_PG16.jsonl (أول3سجلات)؛ محادثة المشرف عنPG16/XML؛ ps (فحص العملية المحلية).
- command_or_method: focused30 tests؛ /workspace/security-venv/bin/python -m pytest -q tests/test_a1*.py tests/test_traceability.py (عملية18248/session94366)؛ /workspace/security-venv/bin/python scripts/check_traceability.py؛ git diff --check؛ sha256sum الملفات4؛ بحث docs عن DG لم يجد ملفاً مستقلاً، فDG405 فيHANDOFF؛ بحث database.py أعادexit2 لأنه غير موجود. المشرف طلب إيقاف regression المعلق وإعادته بصلاحيةnetworkenabled بنفسworktree؛ الإيقاف SIGTERM سيلي تسجيل هذا الحدث. SIGINT مرتان لم ينهياه.
- expected: deterministic tests كاملة؛ no manual model dispatch؛ atomic traceability commit؛ native evidence محددSHA.
- outcome: PARTIAL
- validation: focused30 PASS في4.86s؛ traceabilityقبلcommit checked34/tracked32/violations0؛ git diff --check PASS. regressionالأوسع عرض نحو90 علامةنجاح من110 ثمتعليق تجاوز3دقائق؛ نتيجتهCANCELLED وليستPASS، السبب UNKNOWN (TestClient محتمل فقط). لا تغيير اختبارات لإخفائه. الأمرالدقيق الذي سيعيده المشرف: PYTHONPATH=. /workspace/security-venv/bin/python -m pytest -q tests/test_a1*.py tests/test_traceability.py.
- evidence: المشرف أبلغPG16 الحقيقي4/4 في34.64s علىmanifestالأربعة معG5e4abb004/98817fcf وG7df849b9؛ الأصل والنتائجبعدCommitموثقةفيreportوهذااختبارتركيبالمشرفلاسائرA1branch. CIعلىCommitالجديد NOT_RUN حتىالنشر؛ CI6afoldلايغطيالتغييرالجديد.
- risk_and_security: source_evidence checksumلايمثلattestation؛ authority/contextيبقيانUNRESOLVED؛ لاPHIأونموذجأومواردمدفوعةأوmigration؛ sharedfilesلمتعدل. modeljobworkflow_dispatchفقطوالاختباراتالحتميةكاملةعلىPR.
- rollback: revertذريلتغييراتA1والworkflowguardالمصرح؛noreset/merge/forcepush/deploy.
- next: إيقافالمعلقثمCommitذري؛المشرفيعيدالمجموعةغيرالمكتملةبnetworkenabledوينشرDraft20،ويثبتدليلPG16فيفرعالتكامل.
- decision_status: READY_FOR_INDEPENDENT_REVIEW

### EVENT-20261021-405-05 — إغلاق نتيجة regression الواسعة توثيقياً
- event_id: EVENT-20261021-405-05
- when_utc: 2026-10-21T20:57:46Z (وقت فحص الإيصال؛ XML بدأ عند2026-10-21T20:56:11.553182+00:00)
- actor: Codex / A1 owner agent؛ تنفيذ الاختبارات بواسطة المشرف root
- action: READ / WRITE / HANDOFF
- reason: تفويض المشرف إغلاق النتيجة الفعلية بCommit وثائق فقط قبل النشر؛ عدم تكرار الاختبارات أو تغيير runtime أو hash semantics.
- scope: PR20 detached؛ docs/E4_A1_BRIDGE_AR.md وdocs/engineering/HANDOFF_A1_AR.md وworklog فقط؛ synthetic.
- before_sha: 6aca20dedbd4bcc7f18f9f4737bb9f1da6cc1f27
- after_ref: SELF
- files_or_sources: git HEAD/tree/status؛ docs/E4_A1_BRIDGE_AR.md؛ docs/engineering/HANDOFF_A1_AR.md؛ /tmp/a1-root-regression.xml؛ إيصال root وملاحظة integration_rules عنoutput_fingerprint/created_at.
- command_or_method: git status --short؛ git rev-parse HEAD HEAD^{tree}؛ tail للوثائق؛ head لXML؛ sha256sum XML؛ apply_patch توثيقي. الأمر الذي نفذه المشرف: PYTHONPATH=. /workspace/security-venv/bin/python -m pytest -q tests/test_a1*.py tests/test_traceability.py معnetwork.enabled. لم نعده في هذه الحركة.
- expected: حفظ النتيجة على مصدرها المطابق دون الادعاء بأن نجاحA1 يغلق عائق idempotency لدىG5.
- outcome: PASS
- validation: مصدر الاختبار6aca20dedbd4bcc7f18f9f4737bb9f1da6cc1f27 وtreefb7374f0b665d3dd9369bfa89d5317fb2919c0b7؛ root أبلغ110 PASS في13.89s. XML المرئي يثبت110 tests و0 failures/errors/skipped وsuite13.833s. لم يتكرر التعليق في السياق الآخر؛ السبب UNKNOWN. آخرtraceability على6aca:35 commits/33 tracked/0 violations. الاختبارات في هذه الحركة NOT_RUN لأن الشيفرة لم تتغير.
- evidence: /tmp/a1-root-regression.xml SHA256=5147c7a42c34c4fd202db6e382a9fff6866c157b662e3afb92261266e80fe6b3؛ source manifest4 والـworkflow guard لم يتغيرا؛ CI الجديد ما زال بانتظار نشرDraft20 بواسطةالمشرف.
- risk_and_security: a1_output_fingerprint يشملcreated_at ويتغير معpreview جديد؛ لا نغير دلالته فيA1. عزل trace hashes/run غيرالموثقة عن هويةsnapshot وإثباتRED وإصلاحG5 هي مسؤوليةالمستهلك لدىالمشرف، وليست إغلاقاً ضمنA1. لاmodel/manualdispatch أوPHI أوruntime/test changes أوmerge/deployment.
- rollback: revert توثيقي لهذاCommit فقط؛ لاreset أوforcepush.
- next: Commit ذري للوثائق وworklog، تحققtraceability، ثم تسليمSHA وtree للمشرف للنشر فيPR20 القائم؛ يستمرG5 فيوحدتهالمستقلة.
- decision_status: READY_FOR_INDEPENDENT_REVIEW
