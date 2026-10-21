# E4 — A1 bridge — HANDOFF-20261021-405

الحالة: IMPLEMENTED؛ فحوص A1 المحددة ISOLATED VERIFIED. لا اعتماد مالي أو إنتاجي.

نقطة الاستئناف: PR #20، parent `6af41a04cf887d389656c9ce7ffc4e03b396b5a4`، worktree القائم detached. هذا التقرير لا ينسب CI القديم إلى التغيير الجديد. المشرف مسؤول عن النشر في Draft القائم ومراقبة CI على SHA الجديد، دون Merge أو Deployment.

## ما تغير

- قبول locator الموسع في PR34 بعد إعادة قراءة `source_scope` القائم والتحقق من المؤسسة والأصل وjob وapproval وmapping والصف المؤهل CLAIMS. لا نسقط metadata؛ metadata المحذوفة أو صف PAYMENT/excluded لا تتحول إلى مصدر مقبول.
- السعر الفارغ أو الأرقام غير المؤهلة ينتج عنها `invalid_invoice_row` وreview packet غير مكتمل، مع بقاء القيمة الأصلية فارغة في دليل المصدر. لا اشتقاق unit_price أو invoice_total من الإجمالي.
- إضافة اختيارية متوافقة داخل `mcias.a1.review.v1`: `source_evidence` و`source_evidence_fingerprint`. لا تعديل لدلالات a1_input/output_fingerprint القديمة.
- نقل استدعاء/import `analyze` إلى preview؛ إعادة بناء المصدر عبر `build_a1_snapshot` لا تشغّل التحليل أو backend استدلال.
- `open-weight-inference` في workflow يعمل فقط عبر `workflow_dispatch`؛ synthetic-rules على PR تشمل `tests/test_a1*.py` كاملة. لا dispatch أو تنزيل نموذج في هذه الدورة، ولا تغيير للنتائج المجمدة.

## عقد المنتج والمستهلك المعتمد

اعتمد المشرف العقد بعد موافقة مالك G5. يعيد `build_a1_snapshot` الحقول نفسها التي يحملها packet:

```text
source_evidence:
  claim: source_file_id, source_record_id, source(document_id,sha256,locator),
         field_sources, provider_code, service_code, service_date, currency,
         source_scope(approval_id,mapping_version,sheet_type=CLAIMS)|null
  invoice: document_id, stated_total, source
  invoice_lines[]: line_item_id, kind, code, unit, currency,
                   quantity, unit_price, line_total,
                   source_file_id, source_record_id, source, field_sources
  arithmetic_qualification:
    source_qualified: boolean
    qualified: false
    ruleset_version: a1-deterministic-0.1
    gaps: explicit_adjustment_context, approved_arithmetic_rule,
          valid_itemized_invoice (عند النقص)
  unit_price_authority: NOT_ESTABLISHED
```

كل field source يحمل source_file_id/source_record_id/document_id/sha256/locator، مثل `xlsx:sheet:1:row:2:field:unit_price`. هذا عنوان حقل باسمه الفريد في صف أعيد التحقق منه من bytes الأصلية، وليس bbox صفحة OCR.

`source_evidence_fingerprint = SHA256(canonical(source_evidence).encode('utf-8'))`؛ canonical هو JSON بترتيب المفاتيح، `ensure_ascii=False`, `separators=(',', ':')`, `allow_nan=False`. البصمة checksum وليست توقيعاً أو تصديقاً. يتحقق G5 من الأصل والمؤسسة والصف والقيم على الخادم ويعيد Decimal مستقلاً؛ لا يثق بعلم RULE_ENGINE أو source_qualified وحده. fingerprints القديمة يظل تحققها خارج هذا العقد.

تنبيه المراجعة المستقلة: `a1_output_fingerprint` يشمل `created_at`، ولذلك يتغير بين preview جديد وآخر حتى إذا ثبت المصدر. لا نغير دلالته في A1؛ يملك مستهلك G5 فصل trace hashes/run غير الموثقة عن هوية snapshot الثابتة، مع الاحتفاظ بها كأثر تتبع. اختبار A1 الأخضر لا يغلق هذا العائق؛ إثبات RED وإصلاح إعادة المحاولة يقعان في وحدة G5 لدى المشرف.

سعر ProviderTariff.amount التاريخي يبقى تشخيصاً بلا سلطة سعر وحدة؛ لا نعتمد أحدث نسخة بدل السارية. لا attachment مؤهل يعني invoice_lines فارغة، ولا نصنع فاتورة من claim.quantity×unit_price. غياب سياق الخصم/الضريبة/التقريب والقاعدة المعتمدة يمنع qualification. OCR مرشح، موضع صفحة كاملة، أو ثقة غير معايرة لا تدخل trusted adapter الحالي. لا تنفيذ قرار مالي أو إثبات احتيال؛ مراجعة G6 معلقة وrealized_savings فارغ.

## Manifest نقل الخدمة الدنيا فقط

يسمح مالك A1 للمشرف تركيب الملفات القائمة الأربعة التالية فقط على تجربة PR34، مع توثيق parent أعلاه وSHA هذا التسليم. لا app/API/workflows/migrations أو الفرع الكامل:

| الملف | SHA-256 |
|---|---|
| mcias/agents/__init__.py | 08d2b011543656dbc6b9b668d555687c1b88c157147b5964fca1302b1dc76533 |
| mcias/agents/a1_trusted_input.py | da59f1bc301032748b5e960565944c60083b86f0b139ac48d84eefe0a5153906 |
| mcias/agents/a1_review_packet.py | 313f1194929a16c11e0940138de1d3001825e46e539b32d703bfac1622a68fb8 |
| mcias/agents/invoice_integrity.py | 5bc9c0e042309e1df7b0386c572e0ffe38dab74e6b4aa94442b84393e99f7dba |

## الأدلة والحدود

- baseline قبل التعديل: `tests/test_a1_trusted_input.py tests/test_a1_itemized_decimal_provenance.py`، 19 PASS في5.23s.
- بعد التعديل: الملفان السابقان و`tests/test_a1_native_source_evidence.py`، 30 PASS في4.86s. هذه SQLite/unit tests؛ native gate يستخدم stub صريحاً ولا يمثل PG16.
- تحقق المشرف منفصل: PG16 حقيقي4/4 في34.64s، الملفات الأربعة المطابقة للـmanifest مع G5 `e4abb004`/`98817fcf` وG7 `df849b9`. invoice متسقة ومتعارضة، source-swap معrehash، store غائب. النتيجة UNRESOLVED لكلها؛ source_verified فقط للأوليين، خمس إشارات Decimal للتعارض، event واحد بعدretry، G6hold وG7incomplete بعدCommit. قرأ مالك A1 أول3 سجلات من `/workspace/test2/.e2e-output/A1_G5_NATIVE_PG16.jsonl`، والملخص/XML من المشرف (`/tmp/a1-g5-native-root.xml`). ليس هذا اختبار فرع A1 الكامل أو اعتماداً إنتاجياً؛ المشرف يثبت الدليل في مسار التكامل.
- بعد تعليق المحاولة المحلية وإيقافها، أعاد المشرف الأمر نفسه بصلاحية `network.enabled`: `PYTHONPATH=. /workspace/security-venv/bin/python -m pytest -q tests/test_a1*.py tests/test_traceability.py`. على مصدر `6aca20dedbd4bcc7f18f9f4737bb9f1da6cc1f27` نجح **110/110** في13.89s وفق الإيصال؛ XML `/tmp/a1-root-regression.xml` يثبت110 tests،0 failures/errors/skipped، ووقتsuite13.833s. لم يتكرر التعليق في السياق الآخر؛ السبب غير محسوم، ولا نجزم بأنه خلل شبكة أوTestClient.
- Traceability على `6aca20d`: checked35/tracked33/violations0. لا تغييرات runtime أو tests بعد هذا المصدر؛ التسليم اللاحق توثيقي فقط. CI على Commit الجديد يظل NOT_RUN محلياً إلى أن ينشره المشرف. نتائج النموذج السابقة والـworkflow guard اليدوي لم تتغير.

أول عائق باقٍ: سلطة rule وسياق الحساب المعتمد والمرجع الصريح؛ مالكه G5/G3 بالتنسيق مع مالك العقد. الإغلاق بإثبات المصدر والسياق والقاعدة المعتمدة واختبارها، دون تحويل نقصها إلى مخالفة.
