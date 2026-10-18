# DG-001 — Shared Audit Writer: G3 contract creation integration

## Scope
Use existing `mcias.audit_writer.write_event` for successful manual G3 contract draft creation; record explicitly authenticated, tenant-bound denied contract creation attempts through `record_outcome_independent` **after rollback**. No changes to approval, tariff rules, reference activation, deployment or other MCIAS modules.

## Event contract
- `contract_draft_created`: success, `contract_version` resource ID, tenant and authenticated actor, bounded `version` and `contract_number`.
- `contract_creation_denied`: denied, `contract_version`, authenticated tenant and actor, with bounded `reason_code` (`permission_denied` or `reference_conflict`). No untrusted request body, passwords, access tokens, free-text contract notes, patient details, or raw exception text.
- Successful events share the business DB transaction. 403 permission denials and 409 business conflicts are recorded in independent committed transactions following rollback. Unauthenticated requests with no trustworthy actor identity are outside this integration scope.

## Evidence / acceptance
`scripts/check_contracts_acceptance.py` asserts one creation success, rejection records for duplicate number, invalid date interval and reader forbidden action, persistent PostgreSQL records with organization and outcome, and unchanged import/add/revise acceptance flows. Inspect the exact SHA GitHub Actions run; do not claim PASS until it finishes.

## Limitations
Application-role append-only protection follows existing DB privileges/triggers; no guarantee against PostgreSQL superuser or table owner. Audit is **not system-wide complete**. A separate dedicated audit-writer DB role and durable security audit coverage for unauthenticated failures require future assessment. PR remains draft; no merge, production deployment, finance activation, or real patient data.

## HANDOFF
- STATUS: implementation committed, awaiting exact-SHA CI
- SCOPE: G3 manual contract creation success and denied attempts only
- BRANCH: feat/mcias-input-triactions-e2e, PR #25
- BASE: 934430250f1685f92566009c1e3c4814ce2f9a0f
- CHANGED: mcias/reference_service.py, mcias/reference_api.py, scripts/check_contracts_acceptance.py, this document
- TEST: contracts acceptance strict (PostgreSQL 16 + Chromium), G1–G9, Enterprise
- BLOCKERS: CI outcome pending; all-component audit not implemented
- NEXT: verify exact SHA CI and PostgreSQL audit evidence, remediate confirmed failures only
