# G1 Authentication API — implementation log
Date: 2026-10-10. Branch: feat/g1-foundation.

## Added
- Database-backed login using existing PBKDF2 password verifier and opaque, hashed, 30-minute session token.
- Logout invalidates server-side session.
- Profile endpoint requires authenticated user and server-side `profile.read` permission.
- Synthetic HTTP API tests verify invalid login, default-deny permission, authorized profile access, logout revocation and missing token denial.

## Current API
- POST /api/v1/auth/login — username/password; bearer token on success.
- POST /api/v1/auth/logout — bearer token; revoke session.
- GET /api/v1/auth/me — bearer token and `profile.read`.

## Security limitations blocking G1 acceptance
- Super Admin MFA is not implemented. Do not enable privileged production access.
- Rate limiting, lockout and automated credential-stuffing defense are not implemented.
- No secure bootstrap enrollment, credential rotation, user administration, password reset, centralized session invalidation or hardened reverse-proxy TLS deployment.
- PostgreSQL-level authorization, row isolation and privileged DB role restrictions are not proven.
- Real pg_dump/pg_restore and encrypted document restore drill not executed.
- Test suite currently runs SQLite synthetic fixtures for auth; it is not PostgreSQL integration acceptance.
- No signed human acceptance. CI run for this commit must be inspected before claiming success.

## Evidence
Earlier CI run #21 passed unit and dependency-audit. New API tests were committed later and require their own successful CI evidence. See GATE_STATUS.md.
