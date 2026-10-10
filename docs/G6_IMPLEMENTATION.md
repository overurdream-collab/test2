# G6 Governance — Parallel Engineering Track

Status: **OPEN / NOT ACCEPTED**. This branch is based on unaccepted G5 engineering work. Parallel implementation is authorized for development only, not a waiver of the binding acceptance contract.

Implemented: versioned case and event records, linked immutable G5 snapshot, actor, evidence document reference, tenant checks, separation-of-duties approval guard, objection and selective re-audit request, read API, PostgreSQL migration and CI regression.

**Scope limitation:** request_reaudit is a recorded workflow request, not an automatic recalculation. No new audit snapshot is generated without a separately verified, authorized G5 policy. A held or unverified audit snapshot cannot be approved. Partial approval is only modeled at single-claim case granularity, not batch workflow.

Remaining for G6: configurable approval stages and institution-specific permission matrix; formal objection attachment validation, selective re-audit executor with new snapshot version; batch partial approval totals; concurrency and cross-tenant PostgreSQL tests; human-approved acceptance evidence T10/T11/T12; institutional policies and G1–G5 acceptance.

Do not mark G6 ACCEPTED or production ready based on synthetic CI.
