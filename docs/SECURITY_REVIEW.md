# G1 Security Review — 2026-10-10
Status: PARTIAL, NOT A SECURITY CERTIFICATION.

## Controls implemented in source
- Local AES-256-GCM authenticated encryption for file blobs; random opaque storage identifiers and SHA-256 verification.
- Authenticated encrypted archive helper with tamper detection, file manifest and path checks.
- PBKDF2-HMAC-SHA256 password hashing (600,000 rounds), constant-time digest comparison and random opaque token generator.
- Default-deny rule authorization helpers; written-authorization dependency for activation.
- SQLAlchemy mutation hooks to prevent editing original claim fields and ORM-level audit changes.
- Baseline Alembic migration and automated Python tests added.

## Known gaps — do not deploy to production
1. Full login, MFA, session revocation, lockout/rate limiting, CSRF and credential lifecycle are not integrated with API.
2. ORM mutation hooks do NOT prevent raw SQL or privileged database users from altering protected data. Add PostgreSQL database roles, triggers and append-only storage protections.
3. Written-authorization checks verify linked records, not authentic signatures or role of the actual approving organization head. Add identity/authority and signed-document verification.
4. Backup helper is not a complete PostgreSQL pg_dump/pg_restore disaster recovery workflow; T17 full system restore not yet proven.
5. Key custody, rotation, HSM/OS keyring integration and secure key distribution are not implemented.
6. Upload antivirus, OCR sandbox, resource limits, content-type validation and file-size enforcement are pending.
7. TLS deployment, security headers, threat modeling, network controls, monitoring and penetration testing are pending.
8. No real cross-organization isolation integration test or performance test has been executed.
9. Baseline migration is an initial create_all implementation; future migrations must be explicit operations and tested on real PostgreSQL.
10. CI execution, dependency audit and full tests on the GitHub commit require independent verification.

## Threats and follow-up
- Credential theft: MFA, rate limits, short sessions, revocation, audit.
- Unauthorized data disclosure: row/field checks, strict export controls, local-only AI, network restrictions.
- Database bypass: least-privilege PostgreSQL roles, immutable audit triggers and monitored DB access.
- Ransomware/data loss: offline encrypted backup, restore drills, key escrow and retention policy.
- Malicious upload: quarantine, malware scanning, parser sandbox, resource limits.
- Supply-chain compromise: pinned actions/dependencies, dependency scanning and reproducible builds.

All remaining gaps block G1 acceptance.
