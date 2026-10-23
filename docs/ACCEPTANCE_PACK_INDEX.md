# حزمة السياسات والاختبار والقبول

هذه حزمة مسودات عربية وإنجليزية؛ جميع التوقيعات والنتائج الخارجية غير منفذة. لا تمنح اعتمادًا إنتاجيًا.

- [POLICY_PACK](policies/POLICY_PACK.md)
- [COVER_LETTER](policies/COVER_LETTER.md)
- [CLIENT_REQUIREMENTS](policies/CLIENT_REQUIREMENTS.md)
- [WINDOWS_LAPTOP_GUIDE](WINDOWS_LAPTOP_GUIDE.md)
- [DEPLOYMENT_GUIDE](DEPLOYMENT_GUIDE.md)
- [EXTERNAL_TEST_PLAN](EXTERNAL_TEST_PLAN.md)
- [EXTERNAL_TEST_REPORT_TEMPLATE](EXTERNAL_TEST_REPORT_TEMPLATE.md)
- [UAT_PLAN](UAT_PLAN.md)
- [UAT_SCENARIOS](UAT_SCENARIOS.md)
- [UAT_CHECKLIST](UAT_CHECKLIST.md)
- [PENETRATION_TEST_PLAN](PENETRATION_TEST_PLAN.md)
- [PENETRATION_TEST_SCOPE](PENETRATION_TEST_SCOPE.md)

الأسماء الأصلية عربية، وملفات `_EN.md` مقابلات إنجليزية بنفس معرّف الوثيقة والإصدار. تتضمن الحزمة 13 قرارًا ماليًا FIN-ADR منفصلة عن قرارات المعمارية، و25 سيناريو UAT و15 مجال اختبار أمني. السيناريو UAT-25 محجوب لغياب تنفيذ G5 الإنتاجي.

[سكربت الفحص](../scripts/deploy_check.sh) يستدعي [الفاحص](../scripts/deploy_check.py) دون تركيب أو ترحيل أو تعديل بيانات. نجاحه هندسي فقط. المرجع الملزم: [عقد القبول](ACCEPTANCE_CONTRACT.md)، [حالة البوابات](../GATE_STATUS.md)، [تغطية API](FRONTEND_ROUTE_API_MATRIX.md).
