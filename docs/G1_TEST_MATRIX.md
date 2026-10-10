# G1 automated security and recovery verification

CI executes unit tests, PostgreSQL integration and dependency audit on the same branch. Synthetic tests must not be mistaken for target-environment acceptance.

## Coverage by acceptance requirement

| Requirement | Automated proof | Additional evidence needed |
|---|---|---|
| T06 exclusion edit | denied API and audit event | production permission matrix |
| T07 rule activation | denied API and immutable rule trigger | real head authority and key registry provisioned and independently verified |
| T11 immutable approved claims | ORM and PostgreSQL negative mutation | deployed least-privilege account |
| T17 backup and restore | PostgreSQL pg_dump/pg_restore and encrypted source-file hash | target-environment full restore, encryption-key custody |
| MFA | login TOTP, enrollment, replay, offline dual-signature recovery | independent human identity verification, signed key registry |
| Session security | expiration, revocation, MFA fail-closed | target environment negative penetration tests |
| Tenant and medical fields | default-deny and cross-org negative tests | field permission matrix, all new endpoints reviewed |
| Audit | DB append-only and hash-chained signed checkpoint | external write-only destination and independently controlled signing key |
| TLS | defensive application response headers | TLS reverse proxy and trusted certificate scan |
| Feature flags | server-side permission-backed default-deny | approved per-feature entitlement matrix |

## No premature gate closure
An all-green CI result proves only the exercised code and fixtures. It cannot establish human identity, legal signing authority, physical key custody, production TLS, or operational disaster recovery. G1 remains OPEN until those tests are executed and evidenced in the deployment environment, and G0 approvals and gate signature are recorded.

## Signed production authorization update
Production rule activation now validates a detached Ed25519 signature against a deployment-provisioned trusted-head registry. Negative tests cover missing registry, altered signature, altered rule ID and writable registry. This is code-level verification only: organizational authority and registry custody must be verified in the target deployment.
