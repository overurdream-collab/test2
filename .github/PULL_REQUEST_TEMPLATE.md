## ما الهدف؟ ولماذا؟
اذكر سبب التغيير والقرار المرجعي وتذكرة العمل.

## النطاق والملفات المتغيرة
اشرح وظائف/شاشات/API/جداول التغيير، وما **لم** يتغير.

## التوثيق الإلزامي — DG-001
- [ ] أضفت `### HANDOFF-...` مع Scope / Why / Files / Tests / Result / Risks / Next / Handoff في `docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md` **داخل Commit التغيير نفسه**.
- [ ] حدثت `docs/MCIAS_V2_CURRENT_STATE_AR.md` داخل Commit نفسه.
- [ ] حدثت دليل المطور ومصفوفة القبول وADR حسب ما تغيّر، أو شرحت سبب عدم انطباقها.
- [ ] لا يوجد ادعاء PASS بلا SHA أو رابط اختبار؛ لا بيانات مرضى/أسرار في Git.

## اختبارات وأدلة (أرفق الروابط)
| اختبار | أمر/رابط | نتيجة على SHA الحالية |
|---|---|---|
| Unit / HTTP | | NOT_RUN |
| PostgreSQL / migration | | NOT_RUN |
| UI / browser | | NOT_RUN |
| Security / tenant / permissions | | NOT_RUN |
| End-to-end / CI | | PENDING_CI |

## حالات لم تكتمل / مخاطر / رجوع
بيّن العوائق، والآثار التراجعية، والاعتماد المؤسسي المطلوب وخطة الاسترداد.

## تسليم الاستئناف
**آخر Commit SHA:**  
**الخطوة التالية ومالكها:**  
**مسار البدء:** [الحالة الحالية](../docs/MCIAS_V2_CURRENT_STATE_AR.md) ثم [DG-001](../docs/DOCUMENTATION_GOVERNANCE_AR.md).

> فتح PR ليس اعتمادًا للدمج أو النشر. راجع `docs/DOCUMENTATION_GOVERNANCE_AR.md`.
