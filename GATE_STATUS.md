# MCIAS v2.0 — Gate Status Register
Updated: 2026-10-10. Repository: overurdream-collab/test2.
**Status is based on verified evidence, not intentions or files alone.**

| Gate | Status | Deliverables | Mandatory tests | Verified evidence | Approval |
|---|---|---|---|---|---|
| G0 Architecture & Readiness | OPEN | ADRs, threat model, permission matrix, reproducible environment, policy register | Readiness review | None recorded | Pending |
| G1 Foundation | IN PROGRESS — NOT ACCEPTED | FastAPI/SQLAlchemy/Docker scaffold, baseline migration, permission primitives, encrypted file store and backup archive helper; still missing integrated auth/MFA/RBAC, verified deployment of DB immutability triggers and real pg_dump/pg_restore | T06, T07, T11, T17 + security suite | GitHub CI #15: unit SUCCESS; dependency-audit SUCCESS on commit a33a7257; no PostgreSQL restore evidence | Pending |
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
Local focused development test run: 10 tests passed in 0.83s on 2026-10-10, using a comparable local working tree, NOT a verified exact GitHub commit. GitHub CI #15 (run 38000684160) completed SUCCESS for unit and dependency-audit on commit a33a7257f244f65c3c586095f99afc28d374deed. Real PostgreSQL restore drill and signed acceptance remain outstanding. See docs/CHANGELOG_IMPLEMENTATION.md and docs/SECURITY_REVIEW.md.

## Update policy
A status may change to ACCEPTED only after all criteria in docs/ACCEPTANCE_CONTRACT.md are satisfied and a human approver signs the gate. Never mark PASS merely because tests are present.
