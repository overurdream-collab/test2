# Client data, policy and operational requirements

Document ID: `MCIAS-POL-003` · Version: 1.0 · Status: Draft for review · Language: English

[النسخة العربية](CLIENT_REQUIREMENTS.md) · [Package index](../ACCEPTANCE_PACK_INDEX_EN.md)

## Requirement ownership

The institution appoints an owner, delivery date and verification reference for every item. Initial status is NOT_SUPPLIED / NOT_APPROVED. Real data is not assumed to exist in the repository.

| Group | Institution supplies | Verification condition |
|---|---|---|
| Authority/policy | Delegation limits, 13 decisions, policy version, examples and signatures | Verified signatory authority, independent reviewer, hash and effectivity |
| Contracts | provider_code, version, effectivity, status, annex and source | Stable code; no overlapping approved periods; resolved precedence |
| Tariffs | Contract/version, service_code, amount/currency/period and tariff unit | Nonnegative Decimal; quantity/tax basis resolved |
| Beneficiaries | Pseudonymous token, category, dates and enrollment evidence | Identity lookup retained locally; no names/national IDs in Git |
| Claims | claim_reference, beneficiary_token, provider_code, service_code, service_date, claimed_amount, currency | Reconcile original, hash and row/page provenance; authorize source mappings |
| Evidence | Invoices, attachments, authority documents and annexes | Permission before access; encrypted originals cannot be silently replaced |
| Reference codes | Provider/service types, categories and ICD/CPT/LOINC/SNOMED if used | Version/license/mapping supplied; these are not ready-made system catalogs |
| Operations | Linux/PG16, separate migration/runtime accounts, TLS, local scanner, keys/private paths | Frozen SHA, privilege checks, backup and restore |
| Acceptance | Workload/concurrency/P95, RPO/RTO, browsers and accessibility | Written targets before measurement; no invented SLA |

## Transfer and quality rules

1. Start external tests with synthetic data and fresh isolated databases. Use a separately authorized real-data pilot only after relevant privacy/policy approval. Never mix synthetic/real records; no universal per-row source_type exists.
2. No secrets/medical files in GitHub, public reports or external cloud services. Transfer through institution-owned encrypted channels with hashes, file/row counts and an internal receipt.
3. ISO dates `YYYY-MM-DD`, UTC/ISO 8601 timestamps, UTF-8 text and approved currency codes; money uses exact decimal strings, no floats/thousands separators. Review any Excel precision loss.
4. Supply CSV/Excel/PDF mappings, expected row/page counts, null/duplicate rules and quarantine outcomes. Full count/hash reconciliation is an engineering target; medical/OCR quality thresholds need approval.
5. provider_code/service_code/category_id come from institutional references, not assumed national Enums. Retain original identifiers/versions without changing internal UUIDs.

## Required access matrix

Assign owners for profile.read, ingestion.read/upload, claims.read/import, reference.read/write/approve, reports.read/create/export, governance.*, policies.approve/review/revoke, retention.read/archive and each `medical_fields.<source_column>.read`. These are review groups, not a promise that wildcard names are valid permission codes; match actual API files/coverage. super_admin alone grants neither every permission nor an independence override.

## Receipt and gaps

Record owner, version, permitted use, transfer channel, row count, SHA-256, quarantine errors, linkage results, acceptance/rejection, reviewer/date for each delivery. Quantity/tax, cumulative caps, insurer reconciliation ledger and complete appeal stages require separate engineering if needed. No production G5 execution API exists: signed policy and real data alone do not establish launch readiness.
