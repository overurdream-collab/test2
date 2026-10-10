# G6 Governance — Parallel Engineering Track

Status: **OPEN / NOT ACCEPTED**. This branch is based on unaccepted G5 engineering work. Parallel implementation is authorized for development only, not a waiver of the binding acceptance contract.

Implemented: versioned case and event records, linked immutable G5 snapshot, actor, evidence document reference, tenant checks, separation-of-duties approval guard, objection and selective re-audit request, read API, PostgreSQL migration and CI regression.

**Scope limitation:** request_reaudit is a recorded workflow request, not an automatic recalculation. No new audit snapshot is generated without a separately verified, authorized G5 policy. A held or unverified audit snapshot cannot be approved. Partial approval is only modeled at single-claim case granularity, not batch workflow.

Remaining for G6: configurable approval stages and institution-specific permission matrix; formal objection attachment validation, selective re-audit executor with new snapshot version; batch partial approval totals; concurrency and cross-tenant PostgreSQL tests; human-approved acceptance evidence T10/T11/T12; institutional policies and G1–G5 acceptance.

Do not mark G6 ACCEPTED or production ready based on synthetic CI.

## G6 hardening on G5–G7 feature branch
Separate server-enforced governance action permissions; verified extracted objection documents, controlled reason-code payloads, immutable re-audit event lineage referencing later tenant-matched G5 snapshots and a newly opened G6 case. No automatic G5 recalculation or invented authorization; stage configuration and human approvals remain OPEN.
