# MCIAS G5 → G6 → G7 engineering handoff

Branch: `feat/g5-g6-g7-reporting` (based on `feat/g6-governance`).
Classification: synthetic engineering development; **not production activation**.

## G5
Palermo-2 now fails closed for missing, non-finite, corrupted or malicious financial values; verifies the exact eight-agent roster, summed deduction evidence, provenance and calculation fingerprint. Deterministic Decimal processing, institutional signed grant checking and source immutability are preserved.

## G6
Governance action permissions are separated (`governance.propose`, `governance.approve`, `governance.review`, `governance.reaudit`). Objection evidence must be present, tenant-bound, extracted/reviewed and supported by an original SHA-256 hash; quarantined source cannot establish an objection. A `link_reaudit` event requires a preceding `request_reaudit` and an existing separate G5 snapshot for the same claim and tenant. The API supports generic event creation; a new case is recorded for subsequent decisions. No old event or snapshot is rewritten.

## G7
Immutable versioned reporting, Excel/PDF outputs, dashboard summary API, beneficiary statement API, per-currency financial reconciliation and default-deny field-level export. See G7_IMPLEMENTATION.md.

## Policy blockers
ADR policy pack decisions remain pending. No G5 automatic audit activation, no G6 institutional approval, and no G7 production financial settlement is authorized by this branch. Do not merge to production without formal acceptance and privacy review.

## Exact evidence required
Attach final branch commit SHA, complete unit test/PG-integration/security result URLs, test failure triage and a named institutional reviewer. The earlier G6 CI success applies to its own exact commit, not automatically to this branch.
