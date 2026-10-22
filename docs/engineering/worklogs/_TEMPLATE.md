# قالب سجل حدث إلزامي (ينسخ إلى سجل المشروع اليومي)
### EVENT-YYYYMMDD-NNN — وصف الحركة
- event_id: EVENT-YYYYMMDD-NNN
- when_utc: YYYY-MM-DDTHH:MM:SSZ أو not independently verifiable
- actor: ChatGPT / Codex / Human
- action: READ / RESEARCH / DECISION / WRITE / TEST / FIX / CI / PR / HANDOFF
- reason: لماذا الإجراء
- scope: الفرع / المهمة / الجزء المتأثر
- before_sha: SHA الأب الكامل
- after_ref: SELF
- files_or_sources: المسارات/المصادر جميعًا
- command_or_method: الأوامر أو طريقة التنفيذ؛ NOT_RUN إن لم ينفذ
- expected: معيار النجاح وأثر الإجراء
- outcome: PASS / FAIL / BLOCKED / CANCELLED / NOT_RUN / PARTIAL
- validation: الاختبارات الدقيقة والنتائج أو NOT_RUN
- evidence: الروابط وبصمات النتائج
- risk_and_security: مخاطر ومعلومات غير مؤكدة
- rollback: كيف نرجع بطريقة آمنة
- next: أول إجراء محدد
- decision_status: IN_PROGRESS / TESTED_SYNTHETIC / BLOCKED / READY_FOR_INDEPENDENT_REVIEW / INSTITUTION_ACCEPTED
