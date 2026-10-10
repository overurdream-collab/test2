# G6 / G7 preparatory engineering (NOT GATE ACCEPTANCE)

Binding contract: `docs/ACCEPTANCE_CONTRACT.md`. **G5, G6 and G7 remain OPEN** until each preceding gate is signed. These modules are isolated preparatory implementations, not a transition or production release.

## G6 synthetic prototype
- `mcias/g6_decision_planning.py`: explicit staged proposal, no self-approval, partial holds, evidence references, version fingerprint, and selective objection impact planning.
- T10/T11/T12 unit tests: only impacted claim IDs selected for re-audit; approved source snapshots remain unchanged; held claims excluded.
- NOT YET: durable decision/objection records and DB migrations, tenant-scoped RBAC APIs, authenticated Inputs ingestion, execution of selective re-audits, configurable policy workflow, institutional signoff.

## G7 synthetic prototype
- `mcias/g7_snapshot_reporting.py`: immutable-in-memory JSON report payload and fingerprint, independent claimed = deduction + payable reconciliation, source columns retained in XLSX, tenant and sensitive-field checks.
- T13/T18/T20 synthetic unit tests: frozen values survive later source mutation; source fields retained; unauthorized export denied.
- NOT YET: persisted immutable report versions, complete beneficiary statements, PDF renderer, executive dashboard, server-side export permissions, data lineage, reconciliation against database totals, on-prem scale/acceptance evidence.

## Release control
Do not expose preparatory modules as production routes or mark G6/G7 ACCEPTED. CI results prove only the tested code, not institutional approval.
