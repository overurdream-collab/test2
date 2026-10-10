# MCIAS v2.0 — Engineering work log

## 2026-10-10: Initial test2 baseline
1. Initialized clean private test2 repository and dedicated feat/g1-foundation branch.
2. Added FastAPI app scaffold, PostgreSQL Docker service, models and development-only status endpoint.
3. Recorded G0/G1–G9 implementation and acceptance contract, Golden Dataset requirement and gate register.
4. Added architecture decision register, including unresolved production policy blockers.
5. Added local authenticated AES-256-GCM file storage helper with source checksum verification.
6. Added authenticated encrypted backup bundle helper; does not yet execute pg_dump/pg_restore.
7. Added PBKDF2 password hash verification and opaque token generation primitives; not integrated with login.
8. Extended schema with permissions, role permissions, session tokens, written authorizations and rule versions.
9. Added default-deny rule checks, including written-authorization requirement for activation.
10. Added ORM guards for original claim values and audit-log mutations; database-level enforcement pending.
11. Added initial Alembic baseline and CI workflow with Python tests and dependency audit.
12. Added unit tests for security primitives and governance controls; CI evidence and full on-premises acceptance pending.

## Verification honesty
A separate local engineering harness executed 10 focused tests successfully against a comparable local working tree. This is **not** evidence that the exact GitHub commit passed CI, nor proof of PostgreSQL recovery or G1 acceptance. Record commit-bound CI results before marking any acceptance tests PASS.

## Pending
- Review CI logs and resolve failures on the committed tree.
- Replace development token with integrated auth/MFA and strict RBAC.
- PostgreSQL triggers and database privilege separation.
- Real encrypted pg_dump/pg_restore and source-file restore test.
- Production-grade file scanner and key management.
- Finish G0 ADRs, environment reproducibility and policy decisions.
