# MCIAS v2.0 — Codex / developer execution handoff

**Read-only baseline:** `main` is the existing G1–G9 integrated engineering foundation.  
**Proposed changes:** `feat/temporal-reference-inputs-and-four-outcomes`, [Draft PR #22](https://github.com/overurdream-collab/test2/pull/22).  
**Agent architecture:** [Draft PR #19](https://github.com/overurdream-collab/test2/pull/19).  
**Status:** NOT production-approved. No real medical records, paid services or unauthorized deployment.

**MANDATORY DG-001:** Every functional/doc/config change MUST be one atomic Git commit with a new structured `### HANDOFF-YYYYMMDD-NNN` entry in `docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md` (Scope, Why, Files, Tests, Result, Risks, Next, Handoff), AND an updated `docs/MCIAS_V2_CURRENT_STATE_AR.md`. See [full documentation policy](DOCUMENTATION_GOVERNANCE_AR.md). No undocumented commit; do not claim CI PASS before evidence. This is machine-checked on PRs.

## Mandatory reading order

1. [Arabic start-here architecture & API guide](MCIAS_V2_DEVELOPER_START_HERE_AR.md)
2. [Chronological implementation journal](MCIAS_V2_EXECUTION_JOURNAL_AR.md)
3. [Feature acceptance matrix](MCIAS_V2_ACCEPTANCE_MATRIX_AR.md)
4. [Future document extraction/typed compiler specification](MCIAS_CONTRACT_INTELLIGENCE_AND_RULE_COMPILER_SPEC_AR.md)
5. [G3 reference controls](../mcias/reference.py), [G5 audit flow](../mcias/audit_service.py), [Palermo-2](../mcias/palermo2.py), [G6 governance](G6_IMPLEMENTATION.md), [G7 reporting](G7_IMPLEMENTATION.md)
6. [Institutional acceptance tracker](G0_G9_ACCEPTANCE_TRACKER.md) or the actual relevant tracked gate document in `docs/`; do not assume a gate is closed.

## Immutable product contract

The user demands **clause-per-input-section**, not a list of medical services incorrectly labeled contract clauses. Sections: contracts, providers, beneficiaries, cost-sharing, categories, exclusions, prior approvals and **per-provider** tariff. Each has source provenance, version number, half-open validity `[start, until)` and independent sign-off. Amending a point produces a new version and an append-only closure event. Never DELETE the old point.

Claims use **service_date** to select the historical contract/tariff/version. Provider H1 and H2 may have different prices for the same code on the same date. The authoritative financial workflow is G3 approved contract/tariff + signed G5 AuditPolicy + independent Palermo verification. ReferencePoints are currently an additional consistency layer, **not an alternative authority**, and cannot execute an AI-inferred rate.

Four claim **review outputs**, one file per claim per selected run: `REJECTED_RULE_CERTAIN`, `ACCEPTED_RULES`, `MISSING_ATTACHMENTS`, `HUMAN_REVIEW`. These are not final rejection/payment/fraud decisions. No strict rejection from absent beneficiary unless independent evidence shows the official beneficiary roster was complete for that service date and insurer.

## Safe engineering workflow

1. Inspect current files and compare to the guides above. Report confirmed vs missing functions. Do not trust documentation over code or tested outputs.
2. Work only in a new feature branch from the latest accepted base. Never force-push the reference branch, rewrite migrations used in production, or merge without approval.
3. Implement one typed clause/check at a time. Prioritize truthful rule evaluation and evidence references over model marketing scores.
4. Preserve tenant-scoping, immutable source/claim/report records, RBAC/MFA, no PHI in logs, Decimal arithmetic and policy fingerprint verification.
5. Build negative as well as positive tests (wrong provider, before/after effective dates, overlap, unrelated tenant, invalid docs, missing evidence, spoofed signature, non-finite Decimal and prompt injection).
6. Test migrations on isolated PostgreSQL: `alembic upgrade head`. Existing migration number in PR #22 is `0019_reference_points`; subsequent migrations must have a new revision rather than silently editing a revision already deployed.
7. Run relevant unit/HTTP/PostgreSQL/browser tests plus all CI on the **exact commit SHA**, then record links/results in [journal](MCIAS_V2_EXECUTION_JOURNAL_AR.md).
8. Update developer guide/acceptance matrix whenever a feature changes or a blocker is resolved. Open a Draft PR with exact scope, tests, known limitations and rollback/forward-recovery considerations. Await independent review.

## Implementation backlog and stopping conditions

- **C1 source extraction**: PDF/XLSX/image → clause drafts with exact locations; DOCX requires additional reader/security tests. Do not activate LLM output.
- **C2 typed compiler**: only explicit, institution-approved fields/operators; no eval, dynamic SQL or inferred medical judgments.
- **C3 cryptographic authorization**: institution-approved content-bound signatures for each clause version and effective date; current production activation is deliberately disabled.
- **C4 G3/G5 financial promotion**: sign, verify and reconcile every affected provider tariff, contract precedence, and policy fingerprint; never overwrite original G3 tariffs.
- **C5 complete roster**: certified insurer-period-beneficiary list before certain eligibility-based rejections.
- **C6 Palermo proven failures**: independent verification of deterministic violation evidence, then appropriate case/line-item disposition; AI suspicion alone remains review.
- **C7 G6/G7/UAT**: historical re-audit, 4 exclusive files, appeal lineage and actual savings ledger without double counting.
- **A1 InvoiceIntegrity**: separate agent branch, real inference with synthetic cases, gold data, Precision/Recall/FPR, evidence and security testing; do not move to A2 until reviewed.

**Never claim:** AI extraction implemented, all contractual rules executable, rejection automatically authoritative, all institutional gates signed, or production-ready. None of these is currently demonstrated by PR #22.
