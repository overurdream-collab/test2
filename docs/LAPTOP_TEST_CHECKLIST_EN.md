# Laptop test checklist

Document ID: `MCIAS-LAP-004` · Version: 1.0 · Date: 2026-10-11 · Status: blank checklist for authorized execution

[العربية](LAPTOP_TEST_CHECKLIST.md) · [Plan](LAPTOP_TEST_PLAN_EN.md) · [Runbook](LAPTOP_RUNBOOK_EN.md) · [Report](LAPTOP_TEST_REPORT_EN.md)

## How to use

[x] means execution/evidence collection or a scope-boundary review is complete, not automatically PASS. Record result/evidence/UTC time for every ID in the report. This checklist grants no execution permission; current approval covers documents only. Read plan stop/merge rules first.

## Before execution

- [ ] User approval covers operation/setup/test writes/used files; reference recorded.
- [ ] Operator/reviewer/device/test round identified.
- [ ] No real-data input or another device's private keys.
- [ ] Dedicated database/volumes; existing installation reviewed by owner; no deletion/reset.
- [ ] Branch/SHA pinned; no changes/updates/push/merge during round without new approval.
- [ ] Local NTFS path, ready Docker Desktop Linux/WSL2 and synchronized phone/Windows time.
- [ ] Actual memory configuration/free space recorded; no assumed SLA.
- [ ] Protected local evidence; no transcription/screen sharing for Credentials.

## Core cases

- [ ] **LAP-01**: Authorization/branch/SHA/clean source recorded.
- [ ] **LAP-02**: Actual Windows/Git/Docker/WSL2/browser/resources recorded.
- [ ] **LAP-03**: Authorized first Start/build/migrations/12 claims on fresh DB; ACL/keys protected.
- [ ] **LAP-04**: Ready health; loopback-only API and no DB port.
- [ ] **LAP-05**: Check controls recorded; running containers alone are insufficient.
- [ ] **LAP-06**: Admin MFA success/missing/replayed code denial without secret exposure.
- [ ] **LAP-07**: Reviewer MFA/propose-approve separation/server user-administration denial.
- [ ] **LAP-08**: Reader denied administration; logout revokes protected session.
- [ ] **LAP-09**: Source records without field grant denied with server HTTP 403.
- [ ] **LAP-10**: Correct RTL/LTR/text/tables/forms.
- [ ] **LAP-11**: Light/Dark/focus/keyboard/drawer actually reviewed.
- [ ] **LAP-12**: Admin/institution/mobile/tablet routes without global overflow; gaps disclosed.
- [ ] **LAP-13**: Synthetic contract/tariff stored and contract remains draft.
- [ ] **LAP-14**: Category/token enrollment/date-specific eligibility recorded.
- [ ] **LAP-15**: Upload/SHA/manifest/duplicate handling without multiplication recorded.
- [ ] **LAP-16**: Approved malformed file quarantined with reason and import denied.
- [ ] **LAP-17**: Stage/resume/repeated resume with stable counts and no duplicate claims.
- [ ] **LAP-18**: Traceable report/source/version/currency/authorized export; old snapshot unchanged.
- [ ] **LAP-19**: Stop/Start/Check preserves entered data/keys/accounts.
- [ ] **LAP-20**: Windows/WSL/container memory and build/start/response timings recorded; no OOM/crash.

## Round boundaries

- [ ] **LAP-21**: Complete name/identity registry incomplete and out of scope; no personal data trial.
- [ ] **LAP-22**: Production G5/financial activation/full appeals out of scope.
- [ ] **LAP-23**: 10K/OCR/malware/full backup-restore deferred to separately authorized scope.
- [ ] **LAP-24**: Institutional UAT/PenTest/signatures outside round; G0–G9 not accepted.

## Closure

- [ ] Every core case has an actual outcome/evidence; missing cases NOT_EXECUTED/BLOCKED, never PASS.
- [ ] Demo/API/laptop/CI evidence separated; overlapping test counts not summed.
- [ ] Defects/warnings/skips/reruns recorded; blocking defects closed with evidence.
- [ ] Evidence sanitized of passwords/TOTP/tokens/.env/medical data; no published raw logs.
- [ ] Before/after restart references/counts match; no volume removal/key regeneration.
- [ ] Reviewer completed report/recommendation; decision HOLD if any core condition is unmet.
- [ ] Push/CI authorization and merge authorization separately recorded before action.
- [ ] Trial success did not become institutional acceptance or real-data authorization.
