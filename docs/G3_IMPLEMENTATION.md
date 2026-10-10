# G3 — Reference implementation and acceptance

## Implemented
- PostgreSQL/Alembic 0007 for versioned contracts, provider tariffs, beneficiary categories and enrollment intervals.
- Half-open effective date intervals `[effective_from, effective_until)` and nonnegative NUMERIC tariffs.
- T04: reject overlapping approved contracts for the same organization/provider.
- T05: identify retroactive proposed contracts and affected approved contract IDs; never silently overwrite.
- Draft-to-approved transition requires independently approved written authorization and explicit contract precedence decision. Historical retroactive contracts remain blocked pending documented human impact review.
- ORM immutability checks for approved contracts and approved tariffs; source of truth remains versioned.
- Tenant-checked reference lookup and impact read APIs; synthetic T04/T05 regression tests.

## Mandatory unresolved production decisions
- **BLOCKED:** exact contract precedence across national rules, provider-specific tariffs, exceptions, categories, and effective periods requires documented authorized business decision.
- **BLOCKED:** historical financial impact of retroactive tariffs cannot be computed until claim matching and deterministic financial engine exist. G3 only identifies affected contract versions.
- **BLOCKED:** independent head-of-organization approval workflow must be linked to the existing G1 signed external authorization registry and reviewed in a real deployment.
- **BLOCKED:** human signoff of G1/G2 prerequisite gates is not evidenced; G3 branch is preparatory and remains OPEN.
- Beneficiary enrollment conflict validation, versioned category governance and performance/negative API tests remain required before G3 acceptance.

## Evidence
GitHub branch `feat/g3-reference`; draft PR #3. CI results must be checked against the exact head commit; do not infer acceptance from a passing test suite.
