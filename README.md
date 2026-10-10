# MCIAS v2.0

Official implementation repository. On-premises medical claims financial and administrative audit.

## Status
G5/G6 hardening and G7 reporting engineering are present on this **feature branch**, but every production acceptance gate remains OPEN until institutional authorization and signed acceptance. Synthetic CI success is not production certification.

## Binding constraints
- Separate local PostgreSQL database and document storage per organization.
- Original claims and source files immutable; full provenance and quarantine.
- ReaderAgent -> Palermo-1 -> eight audit agents and deterministic rules -> Palermo-2 -> human approval.
- No external transmission of sensitive records; no autonomous medical or fraud judgments.
- Contract/exclusion activation requires written organization-head approval and Super Admin activation.

See `docs/IMPLEMENTATION_PLAN.md` for acceptance gates and policy blockers.

## G5 → G6 → G7 implementation track

See `docs/G5_G6_G7_ENGINEERING_HANDOFF.md` and `docs/G7_IMPLEMENTATION.md`. Generate only synthetic or institution-authorized development reports. The `/api/v1/reports` endpoints are permission-gated, and original medical columns are denied without individual field permissions. This branch is not a production deployment.
