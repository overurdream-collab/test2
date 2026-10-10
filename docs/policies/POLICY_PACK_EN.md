# Financial decisions and policy pack

Document ID: `MCIAS-POL-001` · Version: 1.0 · Status: Draft for review · Language: English

[النسخة العربية](POLICY_PACK.md) · [Package index](../ACCEPTANCE_PACK_INDEX_EN.md)

## Purpose and approval status

These are 13 **new draft financial/operational decisions**, not renamed architecture ADRs or evidence of client approval. FIN-ADR identifiers are separate from ADR-001…ADR-011. Every decision is `DRAFT / BLOCKED_FOR_PRODUCTION` until individually signed and mapped to implementation. Preparatory work may continue; affected production policies cannot activate while gaps remain.

Governing references: [acceptance contract](../ACCEPTANCE_CONTRACT.md), [gate register](../../GATE_STATUS.md), [route/API coverage](../FRONTEND_ROUTE_API_MATRIX.md). CI cannot sign a decision.

## Approval and change control

1. The financial policy owner reviews every decision, alternatives and reference calculations.
2. An independent reviewer checks legal/accounting consistency and required source data.
3. The organization head or legally delegated authority signs the decision, policy version, document hash, institution scope and effective dates.
4. Engineering maps the decision to the engine; unsupported choices remain BLOCKED until implemented and tested, not resolved merely by changing UI values.
5. The technical administrator executes only within authorized controls and does not supply institutional approval. Preserve older versions, impact reviews and evidence.

Mandatory fields per decision: owner, decision date, selected alternative, rationale, institution, policy ID/version, effectivity, document/SHA-256, independent reviewer, authorized signatory/signature, change impact and acceptance cases/results. No names or signatures are prefilled.

## FIN-ADR-001 — Contract/annex precedence and effective dates

- **Proposed decision:** Approve an explicit priority between contract, annex and signed exception; bind each claim to the version effective on its service date. Retroactive changes require impact review, not replacement of old evidence.
- **Current implementation and limits:** Versioned contracts use half-open effective periods and prevent overlapping approved contracts for the same institution/provider. Legal document precedence still needs an institutional decision.
- **Alternatives to resolve:** Always use the base contract, prioritize the latest signed annex, or permit specific exceptions; resolve conflicts explicitly.
- **Required acceptance evidence:** Conflicting contract/annex, effective-date boundary and retroactive-change cases, each with documented decision evidence.
- **Implementation reference:** [`mcias/reference_service.py`](../../mcias/reference_service.py)

## FIN-ADR-002 — Beneficiary and service eligibility

- **Proposed decision:** Evaluate eligibility on the service date using effective beneficiary/category coverage. Hold incomplete or ambiguous references; never make a treatment decision.
- **Current implementation and limits:** Temporal beneficiary enrollments/categories and overlap guards exist; no complete clinical registry or national service catalog is supplied.
- **Alternatives to resolve:** Eligibility at service, receipt or settlement; service-date evaluation is proposed, not signed.
- **Required acceptance evidence:** Enrollment boundaries, unmapped service and missing category evidence; incomplete data cannot establish an approved payable.
- **Implementation reference:** [`mcias/reference.py`](../../mcias/reference.py)

## FIN-ADR-003 — Tariff, quantity and tax basis

- **Proposed decision:** Define service units, quantity and tax treatment before tariff approval; do not interpret a unit price as a claim amount without evidence.
- **Current implementation and limits:** The current tariff stage caps the remaining amount after exclusion; it is not a generic percentage discount. ClaimEntry has no standard quantity/tax fields; such arithmetic needs implementation if required.
- **Alternatives to resolve:** Unit price, service bundle or line total; a different basis may require engineering before production.
- **Required acceptance evidence:** Multi-unit, tax and bundle examples with independent calculations and finance approval.
- **Implementation reference:** [`mcias/audit_engine.py`](../../mcias/audit_engine.py)

## FIN-ADR-004 — Exclusions and written authority

- **Proposed decision:** Approve exclusion definitions, source, dates and limits with organization-head authority and independent review; an administrator cannot grant themselves authority.
- **Current implementation and limits:** The engine accepts a nonnegative exclusion amount capped by remaining value. Production rule activation uses a signed trust registry; G5 policy grants use a separate mechanism described below.
- **Alternatives to resolve:** Fixed amount, percentage or service list; percentage/medical interpretation is not generalized in the current engine.
- **Required acceptance evidence:** Unauthorized edit, wrong signature, changed source and excessive exclusion: deny/hold without double deduction.
- **Implementation reference:** [`mcias/production_authorization.py`](../../mcias/production_authorization.py)

## FIN-ADR-005 — Deduction order and calculation basis

- **Proposed decision:** Review and approve the supported sequence exclusion → tariff → cap → copay; each stage uses the remaining amount. Another order needs code changes and regression tests.
- **Current implementation and limits:** AuditPolicy.validate rejects other orders. Authoritative financial calculations are not performed in JavaScript.
- **Alternatives to resolve:** Calculate every deduction on the original amount or use another order; these change financial outcomes and cannot simply be selected in the current UI.
- **Required acceptance evidence:** Combined four-stage case, claimed = total_deduction + payable, and independent Palermo-2 reconciliation.
- **Implementation reference:** [`mcias/palermo2.py`](../../mcias/palermo2.py)

## FIN-ADR-006 — Caps and coverage limits

- **Proposed decision:** Define cap level, period and owner. Do not present the current per-claim cap as an annual cumulative beneficiary limit.
- **Current implementation and limits:** Optional policy.cap limits the remaining claim amount. This engine has no governed annual cumulative-cap ledger.
- **Alternatives to resolve:** Per-line/claim, beneficiary/year or contract cap; cumulative accounting needs additional implementation.
- **Required acceptance evidence:** Zero, absent and exceeded caps; no annual-cap acceptance without ledger evidence and concurrency tests.
- **Implementation reference:** [`mcias/audit_engine.py`](../../mcias/audit_engine.py)

## FIN-ADR-007 — Copay and cost sharing

- **Proposed decision:** Approve the percentage, evidence and calculation base. The current percentage applies after exclusions, tariff and cap.
- **Current implementation and limits:** copay_percent accepts Decimal from 0 to 100; the deduction is rounded before subtraction. Fixed/cumulative deductibles are not a generalized feature.
- **Alternatives to resolve:** Percentage of original, percentage of remaining or fixed deductible; deviations from the engine require resolution before activation.
- **Required acceptance evidence:** 0%, 100%, rounding boundaries and invalid percentage; assign financial shares without medical inference.
- **Implementation reference:** [`mcias/audit_engine.py`](../../mcias/audit_engine.py)

## FIN-ADR-008 — Precision and rounding

- **Proposed decision:** The institution selects HALF_UP or HALF_EVEN and precision 0, 2 or 4, and approves stage-by-stage rounding; no accounting convention is assumed.
- **Current implementation and limits:** The engine uses Decimal, database NUMERIC and exact decimal strings in responses. Changes to expected results require review and signoff.
- **Alternatives to resolve:** Round only the final result or each stage; the implemented engine rounds each stage.
- **Required acceptance evidence:** Half-unit cases, currency precision and independent totals; compare signed examples for each policy.
- **Implementation reference:** [`mcias/audit_engine.py`](../../mcias/audit_engine.py)

## FIN-ADR-009 — Currency and conversion

- **Proposed decision:** Approve supported currencies and their code registry; separate currency totals and never aggregate/convert without approved rates and authority.
- **Current implementation and limits:** The engine rejects claim/policy currency mismatch and provides no approved FX. Three-letter validation is not proof of ISO 4217 membership.
- **Alternatives to resolve:** Single currency, separate totals or a conversion ledger; the last requires more data and implementation.
- **Required acceptance evidence:** Two-currency claims and an unregistered code; no misleading combined total.
- **Implementation reference:** [`mcias/reporting_g7.py`](../../mcias/reporting_g7.py)

## FIN-ADR-010 — Missing evidence and exceptions

- **Proposed decision:** Define required evidence by service and amount; hold missing evidence, preserve originals and forbid silent evidence replacement.
- **Current implementation and limits:** Hashes, row/page locators, quarantine and attachments exist. The engine holds incomplete evidence; no general original-document download API is available.
- **Alternatives to resolve:** Immediate rejection, evidence hold or documented exception; a hold must not automatically become a medical decision.
- **Required acceptance evidence:** Preserved malformed source, foreign attachment, objection without/with evidence; complete provenance chain.
- **Implementation reference:** [`mcias/claim_batches.py`](../../mcias/claim_batches.py)

## FIN-ADR-011 — Duplicates, signals and analytics

- **Proposed decision:** Approve duplicate definitions, comparison periods and tolerable false positives. A signal requests review, not a fraud verdict or automatic deduction.
- **Current implementation and limits:** Source duplication, a duplicates audit category and G8 signals/human reviews exist. No generative-AI platform makes binding decisions.
- **Alternatives to resolve:** Exact match, multi-field rules or statistical analysis; each needs its own denominator, evidence and acceptance criterion.
- **Required acceptance evidence:** True duplicate, legitimate similarity and small groups; measure false positives and trace task version/reviewer.
- **Implementation reference:** [`mcias/intelligence_g8.py`](../../mcias/intelligence_g8.py)

## FIN-ADR-012 — Disposition, reconciliation and objection

- **Proposed decision:** Define proposal, review, approval, objection and re-audit authority. Proposers cannot self-approve; calculation verification is not payment or a medical decision.
- **Current implementation and limits:** G6 provides governed immutable event versions and G7 frozen reports. Full appeal/assignment stages and production G5 execution API are unavailable.
- **Alternatives to resolve:** Single review or amount-based approval tiers; a complete multi-level process needs implementation mapping before acceptance.
- **Required acceptance evidence:** Self-approve/reject even after hold, evidenced objection, stable old report and independent engine reconciliation.
- **Implementation reference:** [`mcias/governance_g6.py`](../../mcias/governance_g6.py)

## FIN-ADR-013 — Retention, privacy and destruction

- **Proposed decision:** Propose seven years, defining the start event, legal holds, roles, record scope and independent destruction authority. Written legal/institutional approval is required.
- **Current implementation and limits:** Local monthly archives are encrypted/readback-verified but bounded to 10,000 rows/128 MiB. Null/system-actor logs are excluded; purge and automatic partition conversion are disabled.
- **Alternatives to resolve:** Longer statutory period or record-class periods; destruction cannot activate before legal-hold enforcement and restore validation.
- **Required acceptance evidence:** Independent restore, hashes, tenant isolation and size-boundary tests; quota-counter cleanup is not audit-log deletion.
- **Implementation reference:** [`docs/RETENTION_POLICY.md`](../../docs/RETENTION_POLICY.md)

## Authorization/signatures: three distinct mechanisms

- Production rule activation: Ed25519 over canonical JSON binding institution, approver, authorization, rule, source and source hash; trusted registry is provisioned outside HTTP requests (`production_authorization.py`).
- Detached authorization document: Ed25519 over document bytes matching SHA-256 (`authorization_signatures.py`); do not assume every API uses this helper.
- G5 policy grant: HMAC-SHA256 over `organization_id|policy_fingerprint|approver_id|reviewer_id`, with locally held `MCIAS_G5_POLICY_VERIFICATION_KEY` (`audit_authorization.py`). This implemented engineering mechanism needs institutional assessment; it does not automatically constitute a personal legal signature.

Private keys never enter browser/API payloads or these documents. A scan/email does not activate the engine by itself. Legal authority and reviewer identity must be verified, with trust provisioned out of band through an approved procedure.

## Decision approval register

| Decision | Choice/version | Owner/reviewer | Signatory/signature/date | Evidence | Status |
|---|---|---|---|---|---|
| FIN-ADR-001 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-002 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-003 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-004 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-005 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-006 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-007 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-008 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-009 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-010 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-011 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-012 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
| FIN-ADR-013 | NOT_RECORDED | NOT_RECORDED | NOT_SIGNED | NOT_RECORDED | BLOCKED |
