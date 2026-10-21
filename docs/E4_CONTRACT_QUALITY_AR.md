# E4 — دليل جودة Contract Intelligence، 21 أكتوبر 2026

الحالة: **ISOLATED VERIFIED** لربط القيم النصية؛ **QUALITY BLOCKED** لاستخراج النموذج؛ قبول التكامل والاعتماد البشري غير مثبتين بهذا التسليم.

المالك: Contract Intelligence. الفرع القائم `codex/contract-evidence`، دون فرع جديد. نقطة الاستئناف المحلية `228262d19c914f04aa4a7af1d9c7898e98734cbf`، وشجرتها `0dd3b77db5d52d2317554be5210cddea88d20803` مطابقة لشجرة GitHub `cc0188e9bfa9d94adb9c43b8a38e4482e062a051` التي تحقق منها المشرف. بدأت الشجرة نظيفة؛ آخر عملية مكتملة كانت تبني إصلاح التبعيات المستقل، مع بقاء C35 ومخرجات النموذج السابقة محفوظة.

## الفجوة المثبتة والإصلاح

كان `validate_candidates` يستخدم احتواءً نصيًا جزئيًا لهوية المقدم والخدمة والعملة وتاريخ السريان. أعادت تجربة اصطناعية `verified_source_anchor` للمقدم H1 والخدمة LAB والعملة USD والتاريخ `2026-01-01` مع أن المصدر يحمل H10 وLABORATORY وUSDX و`2026-01-01x`.

اعتمد المشرف توحيد هذين الفحصين مع حدود الرمز الحرفية المستخدمة في C35، داخل validator الموجود. لم يتغير شكل المدخلات أو المخرجات أو أسماء الحالات أو قواعد إصلاح logical_key. يظل التحقق على الاقتباس نفسه في page/image وعلى حقول الصف نفسه في sheet/row. فحص المبلغ العشري لم يحتج إصلاحًا: المبلغ 500 لا يطابق 1500 أو 500.50 أصلًا.

الملفات الوظيفية المملوكة المعدلة: `mcias/contract_intelligence.py` واختبار مستقل جديد `tests/test_contract_source_binding_holdout.py`. لم تتغير source-view أو Gold أو frozen outputs أو prompt أو النموذج.

## التحقق الفعلي

| المجموعة | النتيجة المحفوظة | الدلالة |
|---|---:|---|
| validator الأصلي من Git object عند نقطة الاستئناف، مع holdout الجديد | 10 FAILED، 6 PASSED | خلل الربط الجزئي أعيد إنتاجه دون checkout/reset أو تغيير الشجرة |
| holdout بعد الإصلاح، page وsheet | 16 PASSED | 14 حالة قيمة غير مدعومة محجوبة، وحالتا نص مطابق بقيتا DRAFT_ONLY |
| source-view، validator، gold battery، C32 replay، C33 raw rejection replay، C34 holdout، segments، independent synthetic، scoring | المجموع مع holdout: 93 PASSED، 0 FAILED، 0 SKIPPED | لا انحدار ضمن هذه المجموعة المحددة؛ لا نموذج أو DB أو API integration في هذا التنفيذ |

المدة التي سجلها pytest للمجموعة النهائية 0.764 ثانية، دون احتساب تشغيل البيئة وتحميل التطبيق. بيان كل اختبار ونتيجته وبصمات الملفات محفوظ في [JSON التحقق](evidence/contract403_source_binding_verification.json)، SHA-256: `59b39773977e7019be48694295c73b2c3493d3912f73f792a4d8a415674162a6`.

الأمر الفعلي للمجموعة النهائية:

```bash
PYTHONPATH=. /workspace/security-venv/bin/python -m pytest -q --junitxml=/tmp/mcias-contract403-green.xml tests/test_contract_source_binding_holdout.py tests/test_contract_source_view.py tests/test_contract_intelligence.py tests/test_contract_gold_battery.py tests/test_contract_c32_frozen_replay.py tests/test_contract_c34_rejection_replay.py tests/test_contract_tariff_segments.py tests/test_contract_independent_synthetic.py tests/test_contract_benchmark_scoring.py
```

إعادة إثبات baseline من كائن Git، دون تعديل الملفات الحالية:

```python
import subprocess, sys, types, pytest
baseline = "228262d19c914f04aa4a7af1d9c7898e98734cbf"
source = subprocess.run(["git", "show", baseline + ":mcias/contract_intelligence.py"],
                        text=True, capture_output=True, check=True).stdout
module = types.ModuleType("mcias.contract_intelligence")
module.__file__ = baseline + ":mcias/contract_intelligence.py"
exec(compile(source, module.__file__, "exec"), module.__dict__)
sys.modules[module.__name__] = module
raise SystemExit(pytest.main(["-q", "--tb=no", "tests/test_contract_source_binding_holdout.py"]))
```

## حدود الدليل وسلطة التعرفة

اتفق المنتج مع مالك G5، بموافقة المشرف، على إبقاء العقد الحالي: `DRAFT_ONLY` و`verified_source_anchor` يثبتان ارتباطًا نصيًا فقط. واجهة C35 `mcias.source_value_evidence.v1` توفر SHA/field/record/locator/offsets، وثقة أساسها `UNIQUE_LITERAL_SOURCE_SPAN`، وثقة النموذج `null`، مع `human_review_required=true` و`financial_decision=NOT_AUTHORIZED`.

لا يثبت وجود مبلغ في النص أنه سعر وحدة معتمد، ولا يُشتق سعر الوحدة من إجمالي فاتورة. يجب أن يستهلك G5 شهادة G3 المعتمدة والمكتملة والسارية، بتحديد المقدم والخدمة والعملة والوحدة و`price_basis=unit_price` وسلطة المقارنة. لا يستهلك اقتراح CI مباشرة كمرجعية مالية. هذا الإصلاح لا يدعي إغلاق سلطة unit_price أو الاعتماد أو دليل PDF المكاني الأصلي.

## جودة النموذج والعائق المتبقي

قرئت تقارير C33/C34/C35 قبل التنفيذ. نتيجة C33 الفعلية التاريخية [39142051824](https://github.com/overurdream-collab/test2/actions/runs/39142051824) تبقى TP2/FP0/FN4، Recall 2/6 = 33.33%. تجربة C34 المرفوضة [39481874549](https://github.com/overurdream-collab/test2/actions/runs/39481874549) حققت 1/6 على C33 المجمد، مقابل 2/6 للموجه الأصلي [39481874804](https://github.com/overurdream-collab/test2/actions/runs/39481874804) على SHA نفسه. نجاح CI لا يغير هذه القياسات.

لم يُشغل نموذج في هذه الدورة، ولم تتغير الأوزان أو المخرجات المجمدة، ولا يوجد ادعاء تحسن Recall. أول عائق جودة متبقٍ يملكه Contract Intelligence: R3/R4 يعيدان قيمًا أو هويات غير مؤهلة، وR5/R6 يعيدان اقتباسات مركبة لا توجد في خلية واحدة. الإغلاق التالي يحتاج اختيار دليل حرفي من حقول الصف الموجودة بعقد متفق عليه ثم تقييم مستقل للمخرجات المجمدة؛ لا تخفيف للـvalidator ولا اختلاق أسعار. اعتماد المرجع المالي الكامل يظل لدى G3 والمراجع المخول بالتنسيق مع G5.

التسليم `HANDOFF-20261021-403` يحفظ الشيفرة والاختبارات والبيان والحالة والسجل ذريًا. CI على commit الجديد **PENDING** لدى المشرف؛ لم ينشر هذا الوكيل أو يدمج أو ينفذ PG16 أو يستخدم بيانات مرضى أو موارد نموذج جديدة. راجع المشرف triggers التاريخية قبل النشر لتجنب تشغيل Qwen غير المطلوب.
