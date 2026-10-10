# G3 — Reference | Closure record (2026-10-10)

**Status: OPEN — reference policies and signatures await the institution.**

## Deliverables
- Versioned provider contracts/tariffs, beneficiary categories and effective-date enrollment.
- Temporal overlap controls, PostgreSQL immutability guards, RBAC reference APIs and CSV tariff import.
- T04 conflicting approved versions rejected; T05 retroactive impact identified and independent review required.
- Written-authorization checks and production organization-head signature verification.

## Tests and evidence
- G3 reference, lifecycle, API security, tariff, PostgreSQL guards and signed-authorization regressions.
- Cumulative CI on G4 commit `626640c1496c3bc4c71fa8fd64dfb315d4fd7035`: https://github.com/overurdream-collab/test2/actions/runs/38010322075
- Unit 112 passed / 10 skipped; PostgreSQL integration 65 passed; dependency audit successful.

## Deferred
- Monetary impact calculation for retroactive changes, which depends on the deterministic G5 engine.
- Real contract and tariff source onboarding under approved institution-specific policy.

## Waiting on
- Signed contract-precedence policy, real organization-head authorization and trust registry.
- G1/G2 gate signoffs, operational deployment verification and authorized G3 human acceptance.
