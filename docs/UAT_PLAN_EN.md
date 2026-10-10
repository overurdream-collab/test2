# Institutional user acceptance plan

Document ID: `MCIAS-UAT-001` · Version: 1.0 · Status: Draft for review · Language: English

[النسخة العربية](UAT_PLAN.md) · [Package index](ACCEPTANCE_PACK_INDEX_EN.md)

## Objective and plan status

Evaluate real use, controls, financial results and evidence in the institution's environment under ACCEPTANCE_CONTRACT/FIN-ADR. This is **DRAFT / NOT_EXECUTED**; no assumed testers/signatures. Authority distinguishes limited synthetic engineering acceptance from institutional production-scope acceptance; they are not interchangeable.

## Roles and independence

Institutional UAT owner scopes the work; DBA runs environment; security/privacy authorizes data; role users execute; independent finance reviewer reconciles calculations; organization head/delegate signs gates. Developers assist reproduction but do not sign for the institution. A proposal actor cannot approve it; separate accounts alone do not establish distinct human reviewers.

## Entry conditions

Frozen SHA/hashes/dependencies/hardware, documented external checks, authorized synthetic sources/reference examples, distinct users/access matrix, backup/restore and independent authority. Real financial acceptance additionally needs signed policies/authority/examples and approved execution workflow. Missing conditions are BLOCKED without preventing limited synthetic UI testing.

## Execution and scheduling

1. Scope session: select UAT-01…UAT-25, assign owner/date per case; UAT_SCENARIOS is the minimum set.
2. Data/role session: confirm source/hash/version/identity and expected negative outcomes; no real data in Git/public devices.
3. Role sessions: users execute steps themselves and record expected/actual/evidence/policy version. Amounts come from authorized backend or labeled fixtures, never authoritative UI arithmetic.
4. Exception session: held/unavailable/errors/expiry/objection states; navigable screens are not automatically operational services.
5. Independent finance/security review: retrace evidence and calculations, assess defects/residual risks.
6. Retest fixed SHA with prior regressions, then disposition and per-gate signatures.

No invented dates/duration/closure rates; institution fills schedule. Known-password fixture users are never institutional production accounts.

## Evidence, outcomes and defects

Per case: ID, acceptance type, SHA, role/tester, prerequisites, synthetic source/real-data authority, policy/grant/snapshot/report references, steps, result, UTC time, sanitized evidence/hash, defect/reviewer. Use PASS/FAIL/BLOCKED/NOT_EXECUTED; correct 403 denial can be PASS. Record SKIPPED/unavailability separately.

Classify defects by financial/privacy/availability impact, not appearance alone. Each has owner, reproduction, fix SHA and independent retest. Never change reference outcomes merely to match wrong code without policy review/signoff.

## Exit conditions

All mandatory scoped cases executed/evidenced/reviewed, no critical unresolved defects, agreed residual dispositions and recovery/security/measurement evidence. **UAT-25 is currently BLOCKED**: passing fixtures cannot accept production G5 or all G1–G9. Limited engineering acceptance explicitly names scope/blocked features; it does not activate policy or erase blockers.

Use [scenarios](UAT_SCENARIOS_EN.md), [checklist](UAT_CHECKLIST_EN.md) and [report template](EXTERNAL_TEST_REPORT_TEMPLATE_EN.md). Gate acceptance follows contract sequencing/register; test execution itself does not change GATE_STATUS.
