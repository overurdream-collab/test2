# Unified laptop test plan

Document ID: `MCIAS-LAP-002` · Version: 1.0 · Date: 2026-10-11 · Status: ready for review; physical laptop execution NOT_EXECUTED

[العربية](LAPTOP_TEST_PLAN.md) · [Runbook](LAPTOP_RUNBOOK_EN.md) · [Checklist](LAPTOP_TEST_CHECKLIST_EN.md) · [Report](LAPTOP_TEST_REPORT_EN.md)

## Purpose and scope

Verify the same MCIAS project from `feat/windows-laptop-testing` on Windows 11 with 8 GB RAM and Docker Desktop/WSL2 before deciding whether to merge PR #17. Merging is not a prerequisite. Pin one full SHA throughout the round; a source change starts a new round with affected cases rerun and remaining evidence accounted for.

Current approval covers preparing these documents only. Before execution, record user authorization covering image builds, a fresh test database, generated keys/accounts, authentication, synthetic inputs and stop/restart. Code changes, additional data files, extra test execution, pushing the branch/triggering CI and merging require authorization covering those actions. Commands appearing in documentation are not permission to run them.

The [acceptance contract](ACCEPTANCE_CONTRACT.md) is authoritative; [gates](../GATE_STATUS.md) remain OPEN / NOT_ACCEPTED. This is a laptop-package trial, not institutional UAT or authorization for real data. See [route coverage](FRONTEND_ROUTE_API_MATRIX.md) and the [external plan](EXTERNAL_TEST_PLAN_EN.md) for broader requirements.

## Entry conditions

- Record operator, reviewer, execution authorization and scope in the report.
- Windows 11/8 GB, Git and Docker Desktop in Linux containers/WSL2 mode are ready; record actual versions.
- Clean Git checkout pinned to a reviewed SHA on local NTFS, outside OneDrive/shared folders.
- Dedicated `mcias_laptop_e2e` database and test volumes. Review any existing installation/data/keys before Start; no reset or volume removal.
- Automatic Windows/phone time, TOTP authenticator, modern browser and recorded available disk space.
- Use existing approved synthetic files only. No patient records or real contracts. Generating another file needs approval.
- Malware scanning is disabled in this profile; it provides no malware/OCR quality evidence.

## Roles and data

The operator executes an authorized scope and collects evidence; a reviewer verifies outcomes; the user separately decides on pushing or merging. `SYN-laptop-admin` handles test setup, `SYN-laptop-reviewer` independent review, and the reader has limited access. A super_admin role does not override RBAC or duty separation.

A fresh first setup creates 12 synthetic claims, each 1,000 LYD, and a report holding all of them without authorized payable amounts. Do not confuse this with the separate static `demo.json` display. Optional `--verify-inputs` adds a draft contract, tariff, category, enrollment and a 100 LYD claim; it requires input authorization and raises the expected count to 13 on its first fresh-database run. Repeating it adds further data; it is not a read-only restart.

## Shared scenario register

Operational steps are in the Runbook. Record an independent result, UTC time, sanitized evidence and any defect for every row. LAP-01 through LAP-20 are core cases; LAP-21 through LAP-24 document scope boundaries and are not implicit passes.

| ID | Action/check | Expected result | Required evidence |
|---|---|---|---|
| LAP-01 | Record authorization, branch, SHA and clean source | Authorized scope and pinned version; no main changes | Authorization and Git output |
| LAP-02 | Inspect Windows/Git/Docker/WSL2/resources | Linux containers ready; versions/space recorded | Versions and resource capture |
| LAP-03 | First Start after setup approval | Successful build/migrations and 12 claims in a fresh DB; no exposed keys | Sanitized Start summary and synthetic records |
| LAP-04 | Check local access and ports | Ready health; API on 127.0.0.1 only; no published DB port | Status and health |
| LAP-05 | Authorized Check | TEST_CHECKS_PASS, including runtime role/head/authentication/user-administration denial | Sanitized Check output |
| LAP-06 | Admin MFA login, missing/reused code | Valid login succeeds; missing/replayed code denied | Screen/protected-check result without secrets |
| LAP-07 | Reviewer login and duty separation | Permitted review; denied user administration; separated propose/approve | Sanitized permissions and HTTP 403 |
| LAP-08 | Reader administration denial and logout | Server denial and session invalidation on logout | Check; denied protected request after logout |
| LAP-09 | Request synthetic source records without field grant | Server HTTP 403; hiding navigation alone is insufficient | Protected local probe in Runbook |
| LAP-10 | Arabic RTL and English LTR | Correct direction/text/tables/forms | Two sanitized images |
| LAP-11 | Light/Dark and keyboard/focus | Readable contrast, visible focus, keyboard drawer opening/closing | Images and navigation observations |
| LAP-12 | Admin/institution/mobile/tablet navigation | Intentional routes, no global overflow, truthful unavailable states | Images, browser version and viewport sizes |
| LAP-13 | Enter synthetic draft contract/tariff | Values/version stored; contract stays draft without automatic approval | Sanitized contract/tariff reference |
| LAP-14 | Enter category/token enrollment | References saved and date-specific eligibility checked; no real personal name | Category/enrollment reference and eligibility |
| LAP-15 | Upload valid synthetic file twice | Extraction/manifest/SHA; duplicate detected without record multiplication | document/job/SHA and both states |
| LAP-16 | Upload approved malformed synthetic file | Quarantine/review_required with reason; denied import | State/reason/import denial |
| LAP-17 | Stage/resume batch, repeat resume | Valid rows imported once; count stable on repeated resume | Batch/count and claim references |
| LAP-18 | Read report/evidence and authorized export | Traceable source/version/currency; no invented payable; new input needs a new snapshot to appear in a new report | Snapshot and authorized synthetic export |
| LAP-19 | Stop, Start, Check | Added claims/references/keys/accounts persist without reset | Before/after counts/references and Check |
| LAP-20 | Observe memory/build/start/response times | No sample OOM/crash; actual measurements without invented SLA | Task Manager/docker stats/timings |
| LAP-21 | Complete named identity/beneficiary registry | Outside package scope; incomplete; no personal data entry | OUT_OF_SCOPE and requirement reference |
| LAP-22 | Production G5 execution/policy approval/full appeals | Outside package scope; no financial activation or automatic institutional decision | OUT_OF_SCOPE and API coverage |
| LAP-23 | 10K load/OCR/malware/full backup-restore | Outside this round; separate tooling/databases/later authorization | OUT_OF_SCOPE and external plan |
| LAP-24 | Institutional UAT/PenTest/G0–G9 signatures | Outside round; independent approval and later signatures | OUT_OF_SCOPE and acceptance plans |

## Execution and outcomes

Order: authorization/environment → setup → health/authentication → UI → synthetic inputs → reports → persistence → resources → report review. Run each case once and document each rerun/reason. Missing prerequisites mean BLOCKED, not PASS.

States: `NOT_EXECUTED` not run; `PASS` expected outcome with evidence; `FAIL` executed and deviated; `BLOCKED` prevented by missing permission/environment/capability; `OUT_OF_SCOPE` excluded from this defined round. Never sum CI/laptop or overlapping test counts as one pass total. Separate warnings, skipped cases and demo data.

## Stop and decision rules

Stop on real data, secret exposure, authorization bypass, original/snapshot mutation, data loss or repeated crash/OOM. Keep sanitized evidence; no deletion, repair or key regeneration without new approval. Privacy, authorization and integrity defects block a merge recommendation.

Recommending merge of the laptop package requires evidenced PASS for every LAP-01 through LAP-20 on the same version, closed blocking defects, documented out-of-scope LAP-21 through LAP-24 and human review. Any core FAIL/BLOCKED/NOT_EXECUTED keeps the decision HOLD. A recommendation does not execute a merge; user authorization and final-version CI review are required. Institutional acceptance is separate.
