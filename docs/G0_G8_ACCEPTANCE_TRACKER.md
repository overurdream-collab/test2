# MCIAS — Open Acceptance Register G0–G8

Updated: 2026-10-10. **No stage is formally ACCEPTED without signed human approval and reproducible deployment evidence.** Parallel engineering work is not an implicit waiver of the sequential acceptance contract in `docs/ACCEPTANCE_CONTRACT.md`.

| Gate | Available development evidence | Missing mandatory acceptance evidence | Responsible role | Decision |
|---|---|---|---|---|
| G0 Architecture | PostgreSQL on-premises per organization approved as baseline; ADR index | Signed threat model and readiness review; institution-approved policy pack for precedence, currencies, rounding, retention, load, OCR, medical field access | Institution sponsor + lead architect | OPEN |
| G1 Security & Foundation | Auth/MFA/RBAC patterns, append-only audit, signed authorization tests, backup/restore engineering CI | Production TLS and key custody, trusted head-signature authority, least-privilege runtime, independently verified full restore, human security reviewer | Security lead + institution administrator | OPEN |
| G2 Ingestion | ReaderAgent, original hashes, quarantine, Palermo-1, OCR/extraction test fixtures | Real input inventory, institution-agreed extraction accuracy threshold, human checks on quarantined files, independent source coverage signoff | Data owner + QA | OPEN |
| G3 Reference | Temporal contracts, tariff reference and enrollment guards, signed-approval development tests | Written contract precedence and exception policy, live tariff/version gold dataset, official authority signoff | Contract/legal owner + finance | OPEN |
| G4 Claims | Batch import, idempotent resume, source locators and attachments; synthetic volume tests | Institution-approved target volume/SLA and full operational import/invoice-linkage/UAT | Claims operations + QA | OPEN |
| G5 Audit Engine | Decimal financial checks, eight agents, Palermo-2, formal policy grant controls; engineering tests | Institution-signed accounting basis, order and precision; live golden-claim reconciliation, adversarial performance, human approval | Financial audit head + independent accountant | OPEN |
| G6 Governance | Versioned objections, separate approval actions, linked re-audit request/snapshot development tests | Configurable institution-specific multistage approval, true objection documentation, stage-by-stage separation proof and signed workflow acceptance | Claims head + compliance | OPEN |
| G7 Reporting | Frozen SQL/Excel/PDF versions, Arabic RTL dashboard, source integrity tests; G7 CI evidence recorded in `GATE_STATUS.md` | Approved field/record permissions, signed report formats, local RTL usability testing, high-volume exports and privacy UAT | Reporting owner + privacy officer | OPEN |
| G8 Intelligence | Engine, review-only signals, simulations, Studio task lifecycle, false-positive review and isolated data sources on draft branch | Verify final exact GitHub CI head, labeled institutional dataset, false-positive evaluation/threshold signoff, RBAC authority review, UAT and human acceptance | Audit/analytics lead + independent reviewer | OPEN |

## Gate follow-up process

- No tests are marked **accepted** simply because a Python test exists or a previous branch passed CI.
- All engineering claims must include a **specific commit SHA, exact CI run URL and test outcome**; otherwise mark `PENDING EVIDENCE`.
- Unresolved G0 financial and privacy decisions **must not be silently defaulted**. G8 does not define new deductions, diagnosis policies or sanctions.
- Approval is per institutional deployment; a successful open-source CI fixture is **not evidence** of all on-premise organizations being secure or accepted.
- Prior-gate regressions must run on the same proposed G8 commit. Each missing approval receives an independent owner, signed acceptance criterion and evidence record before the gate can be closed.
- The project remains **PRE-PRODUCTION**. Real data and sensitive signing keys should not be uploaded into public GitHub fixtures.

## Specific next acceptance evidence to collect

1. **Architecture / policy authority (G0/G3/G5):** precedence, accounting basis, currency, rounding and written signatures with verifiable institutional key registry.
2. **Security / privacy (G1/G2/G7/G8):** MFA enforcement, least-privilege permissions per medical field, report exports, source/provenance preservation, local encryption, TLS and independent restore.
3. **Claims operations (G4/G6):** real-scale import, invoice attachment correlation, objection and selective re-audit with repeatable case histories.
4. **Analytics quality (G8):** institution-labeled normal/abnormal cohorts, documented true denominator/baseline, reviewer-labeled false positives, alert threshold calibration and impact analysis, all without automatic adverse decisions.

Review and human signatures remain outstanding; do not alter this record to ACCEPTED without the acceptance contract's full evidence bundle.
