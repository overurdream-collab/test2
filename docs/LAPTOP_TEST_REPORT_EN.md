# Laptop test results report

Document ID: `MCIAS-LAP-005` · Version: 1.0 · Date: 2026-10-11 · Status: PENDING_EXECUTION; final report awaiting actual outcomes

[العربية](LAPTOP_TEST_REPORT.md) · [Plan](LAPTOP_TEST_PLAN_EN.md) · [Runbook](LAPTOP_RUNBOOK_EN.md) · [Checklist](LAPTOP_TEST_CHECKLIST_EN.md)

## Current report state

This register awaits actual Windows 11 testing. Conversation approval covers documentation; this round's execution and authorization are not recorded. No laptop outcomes or review signatures are recorded here. Decision **HOLD**; PR #17 needs a separate decision, not an inference from previous CI.

## Round and environment

| Field | Current value |
|---|---|
| Round ID/start/end UTC | NOT_RECORDED |
| Operator/reviewer/execution approval reference and scope | NOT_RECORDED |
| Approved device/Windows build/actual 8 GB | NOT_RECORDED |
| Target branch | feat/windows-laptop-testing |
| Tested full SHA/Git status before and after | NOT_RECORDED |
| PR | [#17](https://github.com/overurdream-collab/test2/pull/17); verify state during review |
| Git/Docker Desktop/Engine/Compose/WSL2 | NOT_RECORDED |
| Actual Python/PostgreSQL/dependencies | NOT_RECORDED |
| Image ID before/after rebuild/PostgreSQL image | NOT_RECORDED |
| Required/actual Alembic head | 0018_claim_query_indexes / NOT_RECORDED |
| Browser/version/viewport sizes | NOT_RECORDED |
| CPU/disk space/WSL limit/Windows and container memory | NOT_MEASURED |
| Test database/volumes/actual port | mcias_laptop_e2e planned / NOT_RECORDED |
| Data type/files/hashes/input-approval reference | SYNTHETIC_PLANNED / NOT_RECORDED |
| Before/after claim counts/contracts/references/test receipt | NOT_RECORDED |
| Institutional SLA/load/full recovery/UAT/PenTest | OUT_OF_SCOPE for this round |

## Actual outcomes

Do not mark PASS before proving the plan's expectation and recording evidence. Create the detailed record below for every outcome. Out-of-scope rows are scope dispositions, not executed tests or successes.

| ID | Scenario | Outcome | Evidence/defect |
|---|---|---|---|
| LAP-01 | Authorization and version | NOT_EXECUTED | NOT_RECORDED |
| LAP-02 | Environment/resources | NOT_EXECUTED | NOT_RECORDED |
| LAP-03 | Build/setup | NOT_EXECUTED | NOT_RECORDED |
| LAP-04 | Health/ports | NOT_EXECUTED | NOT_RECORDED |
| LAP-05 | Check | NOT_EXECUTED | NOT_RECORDED |
| LAP-06 | Admin MFA | NOT_EXECUTED | NOT_RECORDED |
| LAP-07 | Reviewer MFA/duty separation | NOT_EXECUTED | NOT_RECORDED |
| LAP-08 | Reader/logout | NOT_EXECUTED | NOT_RECORDED |
| LAP-09 | Server source-field protection | NOT_EXECUTED | NOT_RECORDED |
| LAP-10 | RTL/LTR | NOT_EXECUTED | NOT_RECORDED |
| LAP-11 | Themes/keyboard | NOT_EXECUTED | NOT_RECORDED |
| LAP-12 | Navigation/responsiveness | NOT_EXECUTED | NOT_RECORDED |
| LAP-13 | Draft contract/tariff | NOT_EXECUTED | NOT_RECORDED |
| LAP-14 | Category/enrollment/eligibility | NOT_EXECUTED | NOT_RECORDED |
| LAP-15 | Upload/duplicate detection | NOT_EXECUTED | NOT_RECORDED |
| LAP-16 | Quarantine/import denial | NOT_EXECUTED | NOT_RECORDED |
| LAP-17 | Batch staging/resume | NOT_EXECUTED | NOT_RECORDED |
| LAP-18 | Reports/evidence/export | NOT_EXECUTED | NOT_RECORDED |
| LAP-19 | Restart persistence | NOT_EXECUTED | NOT_RECORDED |
| LAP-20 | Memory/timings | NOT_EXECUTED | NOT_RECORDED |
| LAP-21 | Complete named identity registry | OUT_OF_SCOPE | Incomplete; API coverage |
| LAP-22 | Production financial execution/full appeals | OUT_OF_SCOPE | Unavailable in package; API coverage |
| LAP-23 | Load/OCR/malware/full recovery | OUT_OF_SCOPE | Separately authorized plan required |
| LAP-24 | Institutional acceptance/UAT/PenTest | OUT_OF_SCOPE | Independent evidence/signatures required |

Current core summary: **PASS=0, FAIL=0, BLOCKED=0, NOT_EXECUTED=20**. Scope boundaries: **4**, excluded from pass rate. After execution, calculate counts from this round's rows only; a rerun replaces the current result while retaining history, not adding another case.

## Detailed case and rerun record

- Case ID/attempt/full SHA/environment: NOT_RECORDED.
- Operator/reviewer/authorization reference/UTC time: NOT_RECORDED.
- Prerequisites/synthetic-data reference: NOT_RECORDED.
- Steps/sanitized command: NOT_RECORDED.
- Planned expectation/actual observation/HTTP status or measurement: NOT_RECORDED.
- Outcome/FAIL or BLOCKED reason/warnings: NOT_RECORDED.
- Local evidence reference/SHA-256/linked defect: NOT_RECORDED.
- Rerun reason/fix SHA/authorization/result: NOT_RECORDED.

## Defects and measurements

| Defect | Case/severity | Expected/actual/impact | Owner/fix/SHA | Rerun/closure |
|---|---|---|---|---|
| NOT_RECORDED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |

An empty table does not mean no defects before execution. Record first build/later start/response timings, sample size, Windows/WSL/container memory, disk/OOM/crashes. All current measurements are **NOT_MEASURED**; 384/768 MiB container limits are settings, not performance results or SLAs. Privacy, authorization, integrity and data-loss issues are blocking.

## Prior CI evidence — separate from laptop results

Recorded engineering results for previous SHA `04e70f8abada85ecaf994fab3c59760c2a51b763`: all 8 PR jobs succeeded; full combined regression 366 passed, 1 skipped, 14 warnings; 10 JS tests; 59 routes with no reported page_errors/accessibility_violations. Includes Windows PowerShell/ACL checks and Linux Docker execution. These are not physical-device or current-documentation-version results; do not transfer them to LAP rows as PASS.

- [G1–G7](https://github.com/overurdream-collab/test2/actions/runs/38096695794).
- [Regression/browser/handoff](https://github.com/overurdream-collab/test2/actions/runs/38096695797).
- [G9](https://github.com/overurdream-collab/test2/actions/runs/38096695838).
- [Docker/Windows launcher](https://github.com/overurdream-collab/test2/actions/runs/38096695726).

No new CI is run as part of document preparation. If pushing is later authorized, record its SHA/run URLs/results separately without summing overlapping counts.

## Decision and signatures

Reviewer recommendation: **HOLD — core device tests unexecuted**. Conditions: PASS for all core cases on the same version, closed blocking defects, documented scope boundaries, then final-version CI review before merge. Test lead/reviewer/review date: **NOT_SIGNED**. User merge authorization/reference: **NOT_RECORDED**. Merge execution: **NOT_AUTHORIZED_BY_THIS_REPORT**. G0–G9 acceptance or real-data processing: **NOT_GRANTED**.

Keep evidence internally with local permissions. Never attach .env/passwords/keys/TOTP/bearer tokens/live-fixture/credentials/raw logs. Public reports contain sanitized references only. Issue the final report with its round ID/date after execution and review; never replace missing results with assumptions.
