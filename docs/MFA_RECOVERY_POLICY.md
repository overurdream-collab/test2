# MFA recovery and encryption-key custody — G1 security gate

Status: DESIGN ONLY; recovery is deliberately disabled until the controls below are implemented and tested.

## Account recovery
1. No public self-service endpoint may disable MFA using password, email, or a session alone.
2. User opens a recovery request through a verified out-of-band channel. Record request ID, affected account, timestamp, reason, and immutable audit trail; never record medical data in the request.
3. Require TWO distinct, active authorized administrators, neither the affected user nor the requester. Each must reauthenticate with MFA and approve independently. Super Admin cannot approve their own recovery.
4. Verify identity through an organization-approved process external to the compromised session. A second channel must be confirmed before proceeding.
5. Recovery operation must revoke ALL active sessions and existing factors atomically, require fresh MFA enrollment before privileged access, and generate a security alert.
6. Enforce request expiration, one-time execution, anti-replay, lockout, and recovery-specific rate limits. Preserve evidence and notify the affected user.
7. Inactive or unverified users, incomplete approvals, and missing audit evidence must fail closed.

## Key custody and rotation
- Keep MCIAS_MFA_ENCRYPTION_KEY out of source control, logs, backups of application configuration, and user-visible API responses.
- Store keys in an on-premises approved secrets facility; restrict access and record administrative use.
- Implement versioned ciphertext envelopes with key identifiers, authenticated associated data bound to user ID and key version.
- Rotate by decrypting with an explicitly authorized old key and re-encrypting with a new key, within a resumable, audited transaction or controlled batch.
- Never delete an old key until all ciphertext has been migrated and independently verified; verify restore drills and rollback.
- Missing keys, invalid tags, and malformed envelopes must fail closed; never silently reset MFA.

## Acceptance tests (NOT YET PASSED)
- Two distinct approvers required; self-approval and duplicate approval denied.
- Replay, expired requests, stolen sessions, inactive approvers, and wrong organization denied.
- Recovery revokes sessions and cannot bypass enrollment.
- Key rotation success, partial-failure recovery, corrupted ciphertext, and backup restore verified on PostgreSQL.
- Security reviewer and organization owner approve the procedure before enabling any recovery endpoint.
