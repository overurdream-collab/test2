# MCIAS v2.0 — Gate Status Register
Updated: 2026-10-10. Repository: overurdream-collab/test2.
**Status is based on verified evidence, not intentions or files alone.**

| Gate | Status | Deliverables | Mandatory tests | Verified evidence | Approval |
|---|---|---|---|---|---|
| G0 Architecture & Readiness | OPEN | ADRs, threat model, permission matrix, reproducible environment, policy register | Readiness review | None recorded | Pending |
| G1 Foundation | IN PROGRESS — NOT ACCEPTED | Auth sessions, RBAC, MFA verification, login throttling, governance API, PostgreSQL immutability triggers, encrypted archive and real pg_dump/pg_restore drill. Pending: MFA enrollment/recovery and key operations, verified written authorization signatures, deployment hardening and human security review | T06, T07, T11, T17 + security suite | CI #197 (run 38004591655): unit SUCCESS, postgres-integration SUCCESS, dependency-audit SUCCESS. Later security regression is pending CI #211 | Pending |
| G2 Ingestion | NOT STARTED | ReaderAgent, provenance, quarantine, Palermo-1 | T01–T03 + coverage/OCR | None | Pending |
| G3 Reference | NOT STARTED | contracts, prices, beneficiaries, temporal versions | T04–T05 | None | Pending |
| G4 Claims | NOT STARTED | batches, attachments, linkage, missing evidence | T09, T16 + volume | None | Pending |
| G5 Audit Engine | NOT STARTED | rule engine, 8 agents, Palermo-2 | T08, T09 + reconciliation | None | Pending |
| G6 Governance | NOT STARTED | approvals, objections, selective re-audit | T10–T12 + separation of duties | None | Pending |
| G7 Reporting | NOT STARTED | Excel/PDF, dashboard, statements | T13, T18, T20 + reconciliation | None | Pending |
| G8 Intelligence | NOT STARTED | analytics, anomalies, simulations, Analysis Studio | T14, T15, T19 + false positives | None | Pending |
| G9 Release | NOT STARTED | security, performance, restore, docs, training | full regression + human signature | None | Pending |

## G0 policy decision register
| Decision | Status | Consequence |
|---|---|---|
| Contract/annex/exception precedence | UNRESOLVED | Contract activation logic blocked |
| Accounting basis and deduction order | UNRESOLVED | Production financial calculations blocked |
| Rounding, currency and FX | UNRESOLVED | Production payable calculations blocked |
| Document retention | UNRESOLVED | Production retention automation blocked |
| Target load and SLA | UNRESOLVED | Performance acceptance criteria blocked |
| OCR quality threshold | UNRESOLVED | OCR acceptance criteria blocked |
| Medical field permissions | UNRESOLVED | Sensitive reports/exports blocked |

## Evidence log
Local focused development test run: 10 tests passed in 0.83s on 2026-10-10, using a comparable local working tree, NOT a verified exact GitHub commit. GitHub CI #83 (run 38002320745) completed SUCCESS for unit, PostgreSQL integration (including T17 real restore drill), and dependency-audit. T06/T07 API denial and separation-of-duties tests are included. Signed acceptance and independent authorization verification remain outstanding. See docs/CHANGELOG_IMPLEMENTATION.md and docs/SECURITY_REVIEW.md.

## Update policy
A status may change to ACCEPTED only after all criteria in docs/ACCEPTANCE_CONTRACT.md are satisfied and a human approver signs the gate. Never mark PASS merely because tests are present.

## G1 closure review (2026-10-10)
- G1 remains OPEN: the successful CI runs do not substitute for signed acceptance.
- MFA enrollment, confirmation, old-session revocation and fail-closed decryption are implemented. Password/MFA secret responses now carry no-store headers (pending CI verification).
- Database trigger blocks updates/deletions to active rule versions; does not protect against DB owner/superuser bypass.
- Pending blocking evidence: approved G0 architecture and threat model; organization-head signature and authority verification; secure super-admin bootstrap and two-person MFA recovery; versioned key rotation and custody; tenant/record/field authorization integration; least-privilege database service role; whole-system restore of database and encrypted source files with hash verification; TLS deployment and negative security tests; reviewer sign-off.
- Policy decisions remain unresolved and must block only dependent financial/medical features, never silently default.

## Latest implementation notes
- Offline MFA recovery now requires two independently verified Ed25519 signatures, valid identity-evidence digest, non-expired unique request, and replaces the factor while revoking sessions. Key enrollment and identity checks remain organizational operations.
- Detached signature verifier for organization-head authorizations added; production rule activation intentionally stays blocked until trusted key registry and verification are wired into governance.
- Target on-prem TLS, key custody, privileged DB runtime account, and independent disaster recovery are not demonstrated by GitHub CI.

## Engineering test inventory (2026-10-10)
- MFA: privileged enrollment/bootstrap, failed decryption, invalid signature, independent approvers, replay, expiration, key rewrap.
- Authorization: cross-tenant and sensitive-field denial, rule activation denial, detached signed-document integrity.
- Storage: AES-GCM confidentiality and tampering, backup corruption, PostgreSQL and encrypted source recovery.
- Database: immutable approved claims, audit records, activated rules, limited runtime-role negative checks.
- API: no-store and defensive headers, invalid and expired sessions, feature entitlement default deny.
- Remaining acceptance evidence: signed head-authority registry wired to rule activation; operational MFA recovery and key custody; production TLS and DB runtime credentials; independent on-prem restore; G0 approvals and human gate signature.

## G1 production signature verification implementation (2026-10-10)
- Signed rule activation is now wired to `can_activate_rule` in production, backed by `MCIAS_AUTHORIZATION_REGISTRY` and a canonical Ed25519 signature binding the organization, rule, approval, approver and archived source SHA-256.
- Negative tests reject missing trust registry, forged signature, mismatched rule binding and writable registry. API test confirms unsigned activation is denied and rule stays draft.
- Off-host audit checkpoint signatures and tamper-detection tests are present; external audit sink and its custody are not deployed by CI.
- **G1 technical acceptance remains OPEN** pending deployment tests of TLS, real head-key custody and authority, actual backup restore on target hardware, and independently controlled audit receipt. Human signoff remains deferred at user's request.
