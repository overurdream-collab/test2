# MCIAS v2.0 — Gate Status Register
Updated: 2026-10-10. Repository: overurdream-collab/test2.
**Status is based on verified evidence, not intentions or files alone.**

| Gate | Status | Deliverables | Mandatory tests | Verified evidence | Approval |
|---|---|---|---|---|---|
| G0 Architecture & Readiness | OPEN | ADRs, threat model, permission matrix, reproducible environment, policy register | Readiness review | None recorded | Pending |
| G1 Foundation | IN PROGRESS — NOT ACCEPTED | Auth sessions, RBAC, MFA verification, login throttling, governance API, PostgreSQL immutability triggers, encrypted archive and real pg_dump/pg_restore drill. Pending: MFA enrollment/recovery and key operations, verified written authorization signatures, deployment hardening and human security review | T06, T07, T11, T17 + security suite | CI #197 (run 38004591655): unit SUCCESS, postgres-integration SUCCESS, dependency-audit SUCCESS. Later security regression is pending CI #211 | Pending |
| G2 Ingestion | ENGINEERING COMPONENTS PRESENT — NOT ACCEPTED | ReaderAgent, provenance, quarantine, Palermo-1 | T01–T03 + coverage/OCR | None | Pending |
| G3 Reference | ENGINEERING COMPONENTS PRESENT — NOT ACCEPTED | contracts, prices, beneficiaries, temporal versions | T04–T05 | None | Pending |
| G4 Claims | ENGINEERING COMPONENTS PRESENT — NOT ACCEPTED | batches, attachments, linkage, missing evidence | T09, T16 + volume | None | Pending |
| G5 Audit Engine | ENGINEERING VERIFIED — OPEN / NOT ACCEPTED | rule engine, 8 agents, Palermo-2 | T08, T09 + reconciliation | None | Pending |
| G6 Governance | ENGINEERING VERIFIED — OPEN / NOT ACCEPTED | approvals, objections, selective re-audit | T10–T12 + separation of duties | None | Pending |
| G7 Reporting | ENGINEERING VERIFIED — OPEN / NOT ACCEPTED | Excel/PDF, dashboard, statements | T13, T18, T20 + reconciliation | None | Pending |
| G8 Intelligence | ENGINEERING IMPLEMENTED — OPEN / NOT ACCEPTED | analytics, anomalies, simulations, Analysis Studio | T14, T15, T19 + false positives | None | Pending |
| G9 Release | ENGINEERING VERIFIED IN PART — OPEN / NOT ACCEPTED | security, performance, restore, docs, training | full regression + human signature | None | Pending |

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


## G5–G7 parallel engineering evidence (2026-10-10)
- Feature branch: `feat/g5-g6-g7-reporting` built from `feat/g6-governance`. Latest recorded successful full three-job CI at commit `f37cb13f14347fc48c97f4a92d9db422cae8f02e`: https://github.com/overurdream-collab/test2/actions/runs/38058656908 (unit + PostgreSQL integration + dependency audit). Subsequent changes must be checked on their own SHA; CI passing on a prior SHA does not prove a later commit.
- G5: hardened Palermo-2; existing signed policy registry; no policy default activation.
- G6: granular permission checks and immutable re-audit links with objections. Institution-configurable approval stages and formal signoff are still OPEN.
- G7: immutable snapshots, Excel/PDF synthetic reports, summary/dashboard API and protected statements; live RTL dashboard UI, approved reporting format, scaled workload and privacy review still OPEN.
- **Engineering work is not production gate acceptance.** G0 policy pack, earlier gate signatures, reviewer evidence and human organizational authority remain blocking. No production finance rule enabled.

## G7 engineering implementation and reproducible CI evidence (2026-10-10)

- **Status: DEVELOPMENT VERIFIED; FORMAL G7 GATE OPEN / NOT ACCEPTED.** The feature branch contains an authenticated Arabic RTL reporting screen at `/ui/reports`, safe executive summaries, report version archive, minimized claim drilldowns with G5/G6 evidence links, server-authorized beneficiary statements, Arabic Excel and locally rendered Arabic PDF.
- Security: CSP with no inline scripts, no-store sensitive API responses, in-memory access tokens only, same-origin assets, per-field protection for original source exports. No private data or credentials included.
- Financial safety: G7 recomputes G5 Palermo-2 reconciliation independently before including an approved item; held/objection/unverified data cannot enter payable totals. T13, T18 and T20 are implemented and tested, with a real PostgreSQL G7 versioning/tenant/immutability test.
- **Verified CI on commit `74dfe61673ff2599528cdbea0479608c8cd7a593`:** [GitHub run #38060137692](https://github.com/overurdream-collab/test2/actions/runs/38060137692). Unit **187 passed, 14 skipped**; PostgreSQL integration **143 passed**; dependency audit **SUCCESS**; `node --check` included. These exact results cover that specific commit; later documentation-only commits must separately complete CI.
- Institutional policy pack unresolved; G0–G6 human acceptance, written financial authorization, approved medical report permissions, deployment/privacy/performance and Arabic UX review remain prerequisites to production. No real payment or production claims were processed.

## G8 engineering / cross-gate acceptance tracking (2026-10-10)

- Dedicated code branch: `feat/g8-intelligence` stacked on `feat/g5-g6-g7-reporting` via draft PR #9.
- Delivered **engineering code**, not an authorized institutional implementation: deterministic provider/service/month analytical aggregates, low-population suppression, separate currency calculations, Palermo-2/G7 provenance linkage, alert-only signals, what-if scenarios, versioned Analysis Studio task configuration, server-generated synthetic test evidence, independent reviewer activation and append-only manual feedback for false-positive quality measurement.
- PostgreSQL migrations `0015_g8_intelligence` and `0016_g8_signal_review` protect task versions, lifecycle and runs against normal-role updates and cross-organization inserts. A DB owner can bypass triggers and must not be the production application service account.
- Separate Arabic RTL user interface at `/ui/intelligence`. G8 is test-only; default-deny RBAC does not automatically grant access. No AI-driven accusation, payer adjustment or clinical action is authorized.
- Original **G0–G7** signed acceptance requirements remain OPEN, with owners, criteria and blockers summarized in `docs/G0_G8_ACCEPTANCE_TRACKER.md`.
- **G8 acceptance remains OPEN:** synthetic CI is not institution-labeled evidence. Remaining prerequisites are real baseline denominators, independent false-positive calibration, field-level authorization approvals, trusted reviewer authority, target-load test, threat/privacy review, MFA/TLS/backup deployment audit and signed human acceptance.
- CI results should be attached only for an exact completed SHA; intermediate commits and prior CI do not certify the latest branch head.

## G8 exact synthetic CI evidence register (2026-10-10)

- Code commit `7efa4515e1bbc9ea146b3c9a55bc56f97173d7e0`: [full inherited regression](https://github.com/overurdream-collab/test2/actions/runs/38062833679): unit **216 passed / 16 skipped**, PostgreSQL integration **143 passed**, dependency audit **SUCCESS**.
- Same code commit: [G8 focused workflow](https://github.com/overurdream-collab/test2/actions/runs/38062830731): G8 unit/UX/security **29 passed**, G8 PostgreSQL **3 passed**, including actual G7-frozen-report-to-G8-analysis-to-independent-review test. JavaScript syntax and installed wheel assets checked.
- This is **software engineering evidence only**. It does not resolve the prior signed acceptances in `docs/G0_G8_ACCEPTANCE_TRACKER.md` or the G8 signed acceptance with real labeled data, independent false-positive evaluation, institution-configured medical permissions, real workload SLA, production TLS/key custody and verified recovery.
- Post-evidence documentation commits require their own exact-head CI before merge. **All human gate statuses remain OPEN.**

## G9 release-engineering verification and pending institutional acceptance (2026-10-10)

- Branch: `feat/g9-release-hardening`, stacked as **draft PR #10** on still-unaccepted G8 draft PR #9; its dependency chain remains in review. These GitHub changes are **NOT** deployed to a real healthcare insurer.
- Added engineering controls: isolated on-prem TLS preview (loopback 8443 only); non-root API and private PostgreSQL; optional off-line Ed25519 release-receipt validation; file-by-file SHA-256 inventory; read-only target-host preflight; production Swagger/OpenAPI disabled; stricter HTTP headers; hardened tar/AES-GCM backup extraction; synthetic deterministic analytics performance measurement; Arabic training and separate database/source-restore runbook.
- **Verified reproducible CI from SHA `5a12bc836f5bd8cb22145d493d8f130fb67dbc9c`**: [all-gates GitHub regression](https://github.com/overurdream-collab/test2/actions/runs/38064789118): unit **229 passed, 17 skipped**, PostgreSQL **143 passed**, dependency audit **SUCCESS**. [G9-focused GitHub workflow](https://github.com/overurdream-collab/test2/actions/runs/38064789111): security/operations **13 passed** and PostgreSQL runtime-role + independent restore **2 passed**, release artifact checksum verified, Compose configuration checked. These results apply to that exact SHA; newer changes must pass their own CI before merged review.
- Formal G9 status **OPEN / NOT ACCEPTED**: institutional financial policies, medical field permissions, human sign-offs for G0–G8, real target-machine backup/recovery, approved SLA/concurrent load, complete private certified TLS deployment, independently trusted key custody and reviewer authority, pinned and independently audited OCI/dependency artifacts, penetration testing, and signed release approval are missing.
- Authoritative cross-stage evidence register: `docs/G0_G9_ACCEPTANCE_TRACKER.md`; practical deployment and preflight: `docs/G9_RELEASE.md`; recovery: `docs/G9_DISASTER_RECOVERY_AR.md`; Arabic operator training: `docs/G9_OPERATOR_TRAINING_AR.md`.
- **Do not mark G9 or any earlier stage ACCEPTED**, do not merge to main and do not run on real patient claims without organizational approval.
