# G1 — Foundation | Closure record (2026-10-10)

**Status: OPEN — engineering evidence is not human acceptance.**

## Deliverables
- PostgreSQL schema and Alembic migrations; authentication, MFA and server-enforced RBAC.
- Append-only audit logging, immutable original-claim controls, encrypted local file storage, encrypted backup and restore drill.
- T06/T07/T11/T17 safeguards and related security regression tests.

## Tests and evidence
- G1 tests are included in the cumulative GitHub CI suites on G4 commit `626640c1496c3bc4c71fa8fd64dfb315d4fd7035`.
- CI: https://github.com/overurdream-collab/test2/actions/runs/38010322075 — unit 112 passed / 10 skipped; PostgreSQL integration 65 passed; dependency audit successful.
- These aggregate counts are **not** a separately signed G1 test report; skipped tests and deployment-only controls require separate verification.

## Deferred
- On-prem service-account least privilege, encryption-key lifecycle and operational hardening verification.
- Production-grade backup/restore exercise, incident and recovery procedures and deployment security review.

## Waiting on
- Reproducible on-prem evidence, G1 security checklist review and named authorized human gate signoff.
- Acceptance contract: `docs/ACCEPTANCE_CONTRACT.md`; do not mark ACCEPTED based solely on CI.
