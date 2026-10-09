# MCIAS v2.0

Official implementation repository. On-premises medical claims financial and administrative audit.

## Status
G1 Foundation in progress. No production claims or completed tests are asserted.

## Binding constraints
- Separate local PostgreSQL database and document storage per organization.
- Original claims and source files immutable; full provenance and quarantine.
- ReaderAgent -> Palermo-1 -> eight audit agents and deterministic rules -> Palermo-2 -> human approval.
- No external transmission of sensitive records; no autonomous medical or fraud judgments.
- Contract/exclusion activation requires written organization-head approval and Super Admin activation.

See `docs/IMPLEMENTATION_PLAN.md` for acceptance gates and policy blockers.
