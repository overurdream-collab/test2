# MFA security implementation — 2026-10-10

Implemented:
- TOTP helper with constant-time comparison, one-step drift window and monotonic replay counter.
- `mfa_factors` schema plus explicit Alembic migration 0003.
- Super Admin login fails closed unless an enabled MFA factor exists.
- Enrolled ordinary users must also provide valid MFA code.
- MFA factor secret stored as AES-GCM ciphertext; key must be supplied separately through `MCIAS_MFA_ENCRYPTION_KEY` as 64 hexadecimal characters; nonce is prefixed to ciphertext.
- Counter is persisted in the same database transaction as session creation.
- Synthetic tests cover TOTP verification, replay and privileged login denial without MFA enrollment.

NOT IMPLEMENTED / ACCEPTANCE BLOCKERS:
- MFA enrollment and recovery procedure, trusted factor activation, key rotation and hardware-backed key custody.
- Rate limiting, lockout and distributed brute-force protection.
- Verified PostgreSQL migration and restore drill; database roles and audit immutability.
- End-to-end MFA integration tests on PostgreSQL and actual CI results for current commit.
- Privileged role assignment must be limited to trusted bootstrap administrator and logged.
- This work does not imply all vulnerabilities are closed or G1 acceptance.

Operational caution: if the MFA key is missing, configured MFA logins fail closed; do not use a development sample key in production.
