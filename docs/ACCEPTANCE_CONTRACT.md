# MCIAS v2.0 — Binding Implementation & Acceptance Contract
Effective baseline: 2026-10-10. Applies to human developers and AI coding agents.

## Governing rule
**A gate is OPEN until its deliverables are demonstrated in a real executable environment, all mandatory acceptance tests pass, prior-gate regression passes, and reproducible evidence is recorded.** Uploading source code, writing a test, or receiving an unverified agent report is not a pass. No transition to the next implementation gate before signed acceptance of the current one.

## G0 — Architecture & Readiness (prerequisite, not included in 48-week estimate)
- Confirm separate on-premises installations per organization; PostgreSQL; no external transfer of sensitive data; local encrypted source store.
- Establish ADRs for backend/frontend framework, auth/MFA, encryption and key management, migrations, file scanning, CI runner, backup/restore, observability.
- Inventory existing source, document baseline commit, create local reproducible development/test environment and synthetic fixtures.
- Identify policy decisions: contract precedence, accounting/deduction basis, rounding/currency, retention, volumes, OCR thresholds and medical-field access. Unresolved policy must be marked BLOCKED; independent foundation work may continue, but affected production financial rules cannot be activated.
- Exit evidence: ADR index, reproducible setup instructions, threat model, permission matrix draft, test plan, approved readiness review.

## G1 — Foundation (4 weeks estimated)
Deliverables: full approved PostgreSQL schema and Alembic migrations; Auth + MFA for Super Admin; server-enforced RBAC and feature flags; append-only audit/access logs; encrypted local file store; encrypted backup and verified restore.
Mandatory: T06 unauthorized exclusion edit blocked; T07 rule activation without written authorization blocked; T11 approved claim mutation blocked; T17 restore verifies data and file hashes.
Extra mandatory security tests: MFA enforcement and recovery, session expiry/revocation, unauthorized organization/record/field access, encrypted file-at-rest validation, service-account least privilege, API negative tests, backup integrity.
Exit: all above plus migration roundtrip, operational docs and evidence. Scaffolding is not acceptance.

## G2 — Ingestion (6 weeks)
ReaderAgent; original-source SHA-256; page/row provenance; quarantine; Palermo-1; file scanning and completeness manifest.
T01 malformed Excel original preserved and isolated; T02 repeat upload recognized as same or revision; T03 unreadable scanned PDF quarantined with page locator; full page and row coverage reconciliation; measured extraction/OCR accuracy on synthetic labeled fixtures.

## G3 — Reference (4 weeks)
Contracts and versions; provider tariffs; beneficiaries and categories; temporal effective-date constraints; approved rule activation workflow.
T04 overlapping/conflicting approved rules rejected; T05 retroactive rule produces impact analysis and human review, never silent overwrite; contract precedence decision documented before production use.

## G4 — Claims (6 weeks)
Claim batches, attachments, linking and missing-evidence holds, resumable imports, immutable original columns.
T09 mixed-validity claims processed at line level without blocking unaffected claims; T16 interrupted import safely resumes without duplicate financial records; real-scale test against explicitly approved target volumes.

## G5 — Audit Engine (8 weeks)
Deterministic financial engine; eight specialized financial/administrative analysis agents; Palermo-2 independent verification.
T08 no double deduction under interacting pricing, exclusions, caps and cost sharing; T09 independent financial reconciliation and evidence validation. Use Decimal/NUMERIC and approved rounding policy. No AI-only financial deduction or medical verdict.

## G6 — Governance (4 weeks)
Configurable multi-stage approvals, objections, evidence through Inputs, selective re-audit, immutable decision versions.
T10 new objection document traced to original and affected items re-audited; T11 direct approved-claim edits rejected; T12 partial approvals exclude held items. Separation of duties: actor cannot approve their own protected proposal/decision.

## G7 — Reporting (4 weeks)
Versioned Excel/PDF reports, executive dashboard, beneficiary statements.
T13 old report snapshot unchanged after re-audit; T18 original source columns/values retained; T20 unauthorized sensitive-field access/export denied. Independently reconcile report totals to frozen database calculation snapshot.

## G8 — Intelligence (8 weeks)
Historical analytics, review-only anomalies, what-if simulations, governed Analysis Studio.
T14 anomaly is review signal, not fraud accusation; T15 unauthorized access blocked; T19 untested agent task cannot activate. Evaluate false positives, provenance, denominator/baseline and evidence quality. No external sensitive AI transmission.

## G9 — Release (4 weeks)
Full security review, performance/load tests, disaster recovery, documentation, training and on-premises deployment package.
Exit: all-gate regression, vulnerability triage, restore drill, approved SLA performance, reproducible release and signed human acceptance.

## Golden Dataset
Maintain versioned synthetic or properly de-identified fixtures covering normal, malformed, duplicate, temporal-conflict, retroactive-rule, combined-financial, objection, privacy and restore cases. No real patient identifiers in source control. Any engine/rule change must run the full dataset and compare results to approved baselines; expected-result changes require review.

## Quality Gate — all conditions required
1. Deliverables complete and demonstrated end to end, not just committed.
2. Mandatory tests pass in an actual reproducible run, including negative authorization tests.
3. All previously accepted gates' regression suites pass on the same commit.
4. Security/privacy and data-integrity checks pass; critical issues closed.
5. Evidence recorded in GATE_STATUS.md or linked evidence manifest: commit SHA, test name, exact command, environment, CI run URL or signed local log, timestamp, outcome, reviewer.
6. Human authorized approver signs the gate; only then set status ACCEPTED and authorize next gate.
Failure or missing evidence = OPEN/BLOCKED, never inferred PASS.

## Evidence record template
- Gate / test ID:
- Git commit SHA:
- Environment (OS, runtime, PostgreSQL, Docker versions):
- Command and fixture version:
- Timestamp (UTC):
- Actual outcome and assertions:
- CI run URL or tamper-evident signed local log:
- Reviewer / human approval:
- Outstanding defects and disposition:

## Scope and authority
Super Admin manages technical permissions and agent tasks but cannot bypass written organization-head approval for contract or exclusion changes. All originals and approved decisions remain immutable; new versions and source provenance are required. Financial policy gaps remain BLOCKED until documented human authorization.
