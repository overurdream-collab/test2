# DG-001 — G5 INPUTS-FIRST owner handoff

Date: 2026-10-21. Scope: coordinated minimal implementation and synthetic PostgreSQL 16 verification only. Baseline HEAD `bd2d1b0c92a5410466217802be936dd469b3b35f`, owner branch `codex/inputs-first-g5`. No merge/deployment/financial authorization.

## Owned changes and approved exchange

Owned files: `mcias/audit_agents.py`, `mcias/audit_service.py`, `tests/test_g5_agent_order.py`, `tests/test_g5_inputs_first.py`, this handoff, and append-only DG-001 journal/current-state entries.

Use existing `AuditSnapshot.findings` JSON for `audit_state`, all six G3 `reference_certificates`, G2/G4 source pointers, and required/executed/blocked counts. Four contract strings are `VERIFIED_MATCH`, `PROVEN_VIOLATION`, `UNRESOLVED_OR_MISSING_REFERENCE`, `AUDIT_NOT_POSSIBLE`; existing advisory finding statuses and financial calculation statuses remain. No new state table, importer, engine or writer.

G3 supplies `reference_service.applicable_reference_snapshots(db, claim, policy)` with six certificates from the actual owner directive in CAI-01 source contract section 9. G4 supplies `source_scope(db, actor, document_id)`: G5 revalidates approved eligible source membership, exact raw-to-normalized values, locator, original hash, tenant, mapping and scope approval. Claimed evidence must match the approved source; inconsistent source cannot prove tariff violation. Linked attachment hashes and tenant are checked independently.

A tariff result is explicitly scoped to the native approved historical contract/service/currency. A signed policy grant and approved source are required. A local proven discrepancy does not complete the other checks or authorize a deduction, rejection or fraud finding. Duplicate claim references are review signals; absent beneficiary, cap consumption and historical completeness remain unresolved.

The G5 service flushes the immutable snapshot then calls PR #29's existing `write_event` with `claim_inputs_audited`, claim/snapshot/source identities, policy fingerprint and typed certificate references. Shared Audit owns UUID deduplication/privacy validation. Snapshot and event commit together. Cached snapshots revalidate source and references; changed/legacy evidence requires a new policy version rather than rewriting an immutable record.

## Actual verification

- Owned pure regressions: `PYTHONPATH=. /workspace/.venv/bin/python -m pytest -q tests/test_g5_engine.py tests/test_g5_palermo_hardening.py tests/test_g5_adversarial.py tests/test_g5_authorization.py tests/test_g5_registry.py tests/test_g5_lifecycle.py tests/test_g5_policy_drafts.py` → **35 passed, 0 skipped, 0 failed**, 0.29 seconds.
- Root executed `tests/test_g5_inputs_first.py` against isolated PostgreSQL 16.15 database `mcias_inputs_g5` with composed producer working trees → **7 passed**, 11.74 seconds. This preliminary run preceded final G3 signature hardening and fixture hardening; it is not final-SHA CI evidence.
- The fixture now stores/retrieves original reference bytes encrypted, uses distinct authorizations and existing Ed25519 trusted-head signatures for the two historical contract versions, and asserts native signature verification. Root must rerun the seven PG16 cases after final producer commits and this change. No claim of that unexecuted result is made here.
- New PG16 cases cover local tariff match/violation and old applicable version despite a newer version, missing beneficiary/caps/cost sharing, duplicate review, expired reference, structurally inconsistent source, and actual `run_audit` commit/reopen with one PHI-safe event, retry and tenant denial.
- `compileall` on owned changed Python files passed. An early TestClient invocation stalled in the network-restricted sandbox and was stopped; no application failure or success inferred. Root runs network-enabled integration centrally to avoid tool approval queue contention.

Preliminary imported producer fingerprints (SHA-256, not owned/committed here): claim_batches `2a574c22cc95030e0c3c564ddbdab9d3de29aebda3a9e9e44071942692c3ed92`; reference_service `4921f175f90932ff781963a5e57a2e630c83ed717c690165d480c33637df7a2f`; audit_writer `e27ad795dd612a53abff7f2e2d842652e3e55551119f51353a98f3f62e36ba48`; audit_contract `3d2cd99e7e37724b3bb128dc85145ff78e2b102ac8a675cfe1652f61fa58ca61`. Final integration must use owner commits, not these provisional snapshots. G2/G4 final producer commit reported `30d4cac03514236d43b2a879acc6eccdf86245e3`.

## First proven blocker and closure owner

The native G3 schema cannot attest complete dated family membership/coverage, medical/administrative policies, cumulative cap consumption or dispensing history. All six full-family certificates truthfully remain incomplete. Therefore overall `VERIFIED_MATCH` and full claim-audit acceptance cannot be demonstrated; an applicable tariff check can be proven while the whole claim remains held for human review. G3/input owners must provide approved effective-dated completeness/source evidence through an independently authorized followup. G5 then consumes those certificates; no synthetic full-completeness authority is fabricated to make this acceptance green.

Final owner commit SHA and exact-SHA CI URLs are supplied by the coordinator after composition. No merge, deploy, real patient data or automatic financial decision occurred.

## Final composition and conflicting-input guard

The coordinator reran the final signed G3 producer and Shared Audit certificate projection against `tests/test_g5_inputs_first.py tests/test_g5_agent_order.py`: **12 passed**, 8.39 seconds (seven native PG16 cases plus five ordered-check regressions). G3 producer `277cc960bac34127748e69ceccbc65e399d067e5`; Shared Audit producer `77e38498` (full SHA in coordinator report).

Final review added a narrow guard: the verified policy currency and tariff must equal the selected historical provider tariff before a check-local match or violation can be proven. A newer valid provider tariff can conflict with a separately signed policy; this must remain unresolved. A new native PG16 regression selects that newer version and checks HOLD. Compilation passed; coordinator must run this added case on the final composition. No new source completeness or financial authorization is claimed.
