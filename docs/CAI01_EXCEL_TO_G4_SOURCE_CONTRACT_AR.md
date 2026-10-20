# CAI-01 Phase 2 — Excel → G4 Source Contract v0.1
**Status:** ISOLATED DESIGN / NOT APPROVED FOR SHARED INTEGRATION. **Baseline:** PR #31 at 28a51ba7ff4f49da4d83a49b25bd05ee9cb6b13d. **Date:** 2026-10-21.
**Related:** [Audit output contract](MCIAS_CLAIMS_AUDIT_OUTPUT_CONTRACT_AR.md). No merge, deployment, shared code changes, production data or financial automation.

## 1. Confirmed implementation and reuse
- G2 `mcias/ingestion/parsers/excel_parser.py`: read-only openpyxl, `data_only=False`, `keep_links=False`; emits `ExtractedRecord(Locator("sheet", sheet_index, row_index), values)`, sheet indices 1-based, rows start at 2. Rejects formula rows, malformed headers; limits 50 sheets/256 columns/100,000 parsed rows. **It does not classify worksheet meaning or attest sheet name in row locator.**
- G4 `mcias/claim_batches.py`: `stage` checks active organization, document SHA, extraction completion, quarantine, creates idempotent batch; `preview` validates; `resume` rechecks source SHA, locks batch, skips already imported record IDs, chunks inserts. **Currently stages all extracted records, not approved claim-only sheets.** It loads all records for resume, so large-batch performance and memory must be measured.
- `mcias/claim_normalization.py`: seven required canonical English columns, strict ISO date, 3-letter currency, Decimal amount. No trusted arbitrary header map, quantity, unit price, cost-sharing or clinical semantic validation.
- Existing isolated `mcias/claims_batch_preflight.py` is a read-only diagnostic selecting explicit sheet indices, detecting malformed rows and candidate duplicates. Selection has no approval/source-SHA binding and is **not** connected to G4.
- PR #25 at `8a616f7f68f506df08deccd62a9faa7d7ec89272`: `docs/DG-001_G2_SOURCE_REVIEW.md` establishes authenticated G2 records+locators and human review for contract drafts, not an approved Excel claims sheet-classification service. `docs/MCIAS_UNIFIED_INPUTS_AUDIT_REQUIREMENTS_AR.md` mandates tenant scope, historical revisions, immutable audit and per-beneficiary family/coverage. `mcias/audit_writer.py` is a shared audit asset on an **unmerged** branch. Do not assume any PR #25 claims importer is already implemented.

## 2. Contract objects (design only)
`SourceManifest`:
```json
{
  "schema_version":"cai01.source.v1",
  "organization_id":"org-A",
  "document_id":"doc-1",
  "source_sha256":"64 lowercase hex characters",
  "extraction_job_id":"job-1",
  "extraction_manifest_hash":"64 lowercase hex characters",
  "source_format":"xlsx",
  "worksheet_inventory":[
    {"sheet_index":1,"sheet_name":"Claims","sheet_type":"CLAIMS","classification":"APPROVED"},
    {"sheet_index":2,"sheet_name":"Payment","sheet_type":"PAYMENT","classification":"APPROVED"},
    {"sheet_index":3,"sheet_name":"Family","sheet_type":"FAMILY_SUMMARY","classification":"APPROVED"}
  ],
  "column_mapping_version":"approved-map-v1",
  "approved_by":"authorized-actor",
  "approval_event_id":"shared-audit-event",
  "approved_at":"ISO-8601 timestamp"
}
```
`SourceRowDecision`:
```json
{
  "organization_id":"org-A",
  "document_id":"doc-1",
  "source_sha256":"64 lowercase hex characters",
  "extraction_job_id":"job-1",
  "source_record_id":"g2-record-id",
  "sheet_index":1,
  "sheet_name":"Claims",
  "excel_row":2,
  "sheet_type":"CLAIMS",
  "row_disposition":"ELIGIBLE_FOR_G4",
  "disposition_reason":"VALID_CANONICAL_CLAIM_ROW",
  "mapping_version":"approved-map-v1",
  "claim_line_key":"deterministic-source-key",
  "claimed_amount":"120.00",
  "currency":"USD",
  "decision_event_id":"shared-audit-event"
}
```
Allowed sheet types: `CLAIMS`, `PAYMENT`, `FAMILY_SUMMARY`, `OTHER`, `UNKNOWN`. Allowed row dispositions: `ELIGIBLE_FOR_G4`, `EXCLUDED_NON_CLAIM`, `HOLD_UNCLASSIFIED`, `HOLD_INVALID`, `HOLD_SOURCE_CONFLICT`. `UNKNOWN` never routes to G4. A claim row is eligible only with verified source, approved sheet and mapping, strict G4 normalization, and authorized tenant context. PAYMENT and FAMILY_SUMMARY are excluded **from claims import**, but retained as source evidence for reconciliation; their amounts are not counted in total claims.
- Row identity: `(organization_id, document_id, source_sha256, extraction_job_id, source_record_id)` with locator uniqueness `(document_id, source_sha256, sheet_index, excel_row)`. Stable import key derived from these fields and `mapping_version` (reprocessing same row with different mapping must version the decision, not create duplicate financial claims).
- For CSV, `sheet_index/name/type` are not inferred: use explicit `CSV_DATA` pseudo-sheet and `row` locator. No cross-tenant SHA-based access.
- Manifest must be cryptographically or transactionally bound to exact document SHA, extraction job/manifest, sheet inventory (names and indices), approved column map and actor authorization; any change invalidates approval. No trust in client-supplied approval flags. Sheet names must be read from a verified inventory; existing G2 row locator alone is insufficient.

## 3. Safe flow and invariants
1. G2 ingest/extract and preserve source/quarantine; record every sheet and physical data-row position (including empty, formula and quarantined rows) in a **coverage ledger**. Current parser does not provide all needed coverage detail; no fabricated counts.
2. Authorized reviewer approves typed sheet inventory and column mapping tied to source SHA and extraction version, through existing governance/audit services.
3. CAI-01 preflight reconciles every extracted/quarantined row to exactly one disposition; no auto-selection by header/name/amount, no silent skip. Source with unknown worksheet type or missing coverage proof stays BLOCKED.
4. G4 adapter (future shared change) must query approved decisions **server-side** by organization, source SHA, extraction job and mapping version; only `ELIGIBLE_FOR_G4` reaches `stage/preview/resume`. Must not rely on a client-filtered list. Existing `stage`/`resume` do not enforce this: **integration BLOCKED**.
5. Atomic claim insert + unique source-row key + version-aware import ledger + idempotent resume, with per-row rejection persisted via shared audit; verify tenant authorization on every access and background job. No cross-organization claim or evidence link.
6. G5 consumes immutable claim snapshot with original locator and historical G3 references; does not infer a missing claim as valid. Human approval/financial decisions remain G6 and shared audit responsibilities, independent of audit classifications.
7. Report all five exclusive classes `NO_DETECTED_FINDINGS`, `HUMAN_REVIEW_REQUIRED`, `MISSING_EVIDENCE`, `UNABLE_TO_AUDIT`, `HUMAN_APPROVED_REJECTION`; immediate deterministic `IMMEDIATE_REJECTION_RECOMMENDED_PENDING_APPROVAL` is a separate subset indicator, never a financial rejection.

## 4. Source and money reconciliation
For each source file, record `physical_data_rows`, `extracted_rows`, `quarantined_rows`, `blank_rows`, `unaccounted_rows`. Require:
`physical_data_rows = extracted_rows + quarantined_rows + blank_rows + unaccounted_rows`; **accept only when unaccounted_rows=0**, and where the original physical row count is verifiable. Blank rows are not claims.
`extracted_rows = eligible_claim_rows + excluded_non_claim_rows + held_rows`.
`eligible_claim_rows = imported_claim_rows + import_pending_rows + import_failed_rows` (mutually exclusive, latest snapshot).
Per currency, `sum(eligible claim line amounts) = sum(imported amounts) + sum(pending amounts) + sum(failed amounts)`, using Decimal and unique source-row identity; unknown amounts are tracked as `UNQUANTIFIED` and do not create false equality.
`PAYMENT` and `FAMILY_SUMMARY` are separate reconciliation dimensions; their totals must not be added to claim totals or assumed equal to them.
A reconciliation manifest includes source hash, counts, currency subtotals, held/unquantified counts, decision version, and complete/blocked flag. `G4_READY` requires all scope/authorization/count invariants, not merely successful normalization.

## 5. Compatibility / file ownership matrix
| System | Reusable asset | Gap / shared file requiring supervisor approval |
|---|---|---|
| G2 | `mcias/ingestion/parsers/excel_parser.py`, extracted record locators, quarantine, job manifest | worksheet name/inventory and physical-row coverage changes: parser, `mcias/ingestion/schemas.py`, ingestion models |
| PR #25 | human source-linked review pattern, tenant authorization, historical input requirements, `mcias/audit_writer.py` | source approval/tenant permission and shared audit writer interfaces: PR #25 owners |
| G4 | `mcias/claim_batches.py`, `mcias/claim_normalization.py`, `mcias/models_claims.py` | server-side approved-row filtering, uniqueness/ledger and transaction model: G4 owner |
| G3 | dated policy/eligibility/tariff reference services | approved effective-dated reference binding: G3 owner |
| G5 | `mcias/audit_engine.py`, `mcias/audit_agents.py`, snapshot/policy checks | immutable claim snapshot adapter and batch audit consumer: G5 owner |
| Shared Audit / PR #29 | unified audit contract and append-only event intent | event schema/writer, consumer ownership, Alembic migrations: shared audit owner |
| G6/G7/G8 | existing authorization/reporting/independent checks | review decisions, dashboard query and independent verification: respective owners |
| DG-001 | isolated execution journal/current state | `docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md` and `docs/MCIAS_V2_CURRENT_STATE_AR.md` overlap other draft branches; AI CTO coordinates merge |
All shared paths above require AI CTO approval before editing; **no shared code is modified in this phase**.

## 6. Synthetic acceptance plan (NOT EXECUTED)
- XLSX: claims + payment + family summary + unknown sheet; ensure only approved CLAIMS enter G4 and all rows accounted for.
- Changed SHA, renamed/reordered sheet, stale mapping, forged client approval, mixed-tenant document/record, duplicate locator/record ID: block.
- Formula row, invalid header, blank/hidden row, truncated extraction, quarantined item: explicit coverage, never silent loss.
- Amount tests: two currencies, Decimal precision, zero amounts, missing amount, duplicate claim line, multi-finding exposure; no cross-currency sum.
- G4: restart mid-chunk, concurrent resume, repeated same source, corrected mapping version; exactly-once ledger and no duplicate claim entries.
- G5: historical G3 snapshot, missing evidence, unauditable, clean, review, human-approved rejected, proposed rejection pending; no auto-financial action.
- Performance: 10k/100k row fixtures (subject to G2 limit), page/cursor exhaustive counts, runtime/memory profile and no truncated exports.
- Security: role/tenant/organization enforcement, immutable decision events, unauthorized reviewer denial, source hash tamper.
**Pass criteria:** 0 unaccounted rows, exact per-currency reconciliation, no unapproved row reaching G4, no duplicate financial claim, no cross-tenant exposure, all five output categories preserved. Any unsupported coverage or source-attestation invariant means BLOCKED.

## 7. Phase 2 multi-batch synthetic verification design — supplemental, NOT EXECUTED
**Scope:** synthetic fixtures only; reuse G2 parser/G4 staging/G5 engine, no parallel parser/engine and no shared branch edits.
- `BATCH-A`: organization A, 3 worksheets: CLAIMS (6 physical data rows: 4 valid, 1 invalid, 1 formula/quarantine), PAYMENT (2 rows), FAMILY_SUMMARY (2 rows). The approved manifest must admit exactly 4 valid claim rows; excluded 4 non-claim rows; quarantined/held 2 claim rows; no payment/family amounts added. Require physical row ledger from G2 before treating these exact figures as machine-verifiable.
- `BATCH-B`: same organization A, separate file/SHA with 4 valid claim rows: 1 repeated claim line from A (candidate duplicate), 1 tariff discrepancy, 1 member-specific copay/coinsurance, 1 benefit cap crossing. Verify G4 source-key idempotency **and** G5 semantic duplicate candidate independently; distinct source rows alone do not prove separate valid claims. Compare reference version effective at service date; absent approved tariff/cost-sharing/cap policy → `MISSING_EVIDENCE` or `UNABLE_TO_AUDIT`, never automatic financial rejection.
- `BATCH-C`: organization B with overlapping claim references and beneficiary tokens, plus family members with different classes/coverage windows. No cross-tenant matches, reads, references, duplicate suppression or financial aggregation. Verify primary employee is also a beneficiary but dependents do not inherit eligibility/coverage automatically.
- `BATCH-D`: organization A resumed import after injected failure at chunk boundary; repeat same file and changed approved mapping version. Confirm stable source identity, transactionally committed checkpoints, no repeated ClaimEntry, durable rejected/held rows and accurate reconciliation.
- G5 output expectations: five exclusive audit classifications preserved and `financial_decision_status` independent; show financially approved claims without clearing findings. Suggested rejection always awaits authorized human decision; no unapproved death reference or rejection policy is simulated as authoritative.
- Fixture assertions: `physical_rows = extracted + quarantined + blank + unaccounted`, `unaccounted=0`; `extracted = eligible + excluded + held`; `eligible = imported + pending + failed`; per-currency Decimal money conservation, source-key uniqueness, no duplicated financial totals, immutable event provenance and authorization. Use explicit input amounts in fixtures; do not invent measured financial savings.

## 8. Large-batch architecture and acceptance gates (design only)
- G2 parser currently enforces 100,000 row ceiling and 50-sheet limit. Never claim >100,000-row support; reject oversize input with explicit status and chunk/file partition plan subject to owner approval.
- G4 `resume` currently materializes all `ExtractedSourceRecord` rows via `.all()`, and constructs `already` as a full set. Proposed change **requires G4 owner approval**: keyset pagination by immutable record ID, bounded chunks (e.g. 100–1,000 after profiling), indexed `(organization_id, job_id, record_id)` access, server-side approved-row predicate and persistent import ledger.
- Atomic commit per bounded chunk; idempotency/uniqueness on `organization_id + document_id + source_record_id` with explicit mapping-version revision semantics, concurrency locking, retries and checkpoint cursor; do not advance cursor until inserts, rejects and shared audit events commit together. Avoid unsafe cross-transaction 'exactly once' claims until proven with PostgreSQL.
- Separate source-row exclusion/hold ledger from G4 ClaimEntry; do not count non-claim sheets in `ClaimBatch.record_count` as accepted claims. G4 `stage`/`resume` currently count all G2 extracted records, so design **cannot pass acceptance without future shared changes**.
- Required load test sizes: 2k, 10k, 50k, 100k synthetic physical rows, with runtime, peak RSS, SQL count, pagination completeness, resumability and zero duplicate inserts measured; thresholds must be agreed with owner, not invented. Verify PostgreSQL 16, role/tenant isolation, two concurrent workers, rollback and retries.
- Dependency order: A1 PR #20 evidence integrity/medical invoice safety (read-only consumer contract); PR #25 G2 source-linked review, identity, historical inputs and permissions; G3 dated beneficiary/tariff/copay/cap references; G4 approved-row importer; PR #29 Shared Audit event schema/writer; G5 existing rules; G6 authorized decisions; G7 report projections; G8 independent E2E validation. All draft branches remain untouched.
- Review decisions requested from AI CTO: trusted worksheet inventory + human approval ownership; source coverage/row event schema; G4 server-side import filter and unique key; semantic duplicates across batches; effective-date reference snapshot; Shared Audit atomicity and permission scope; large-batch performance targets; security dependency upgrade owner.
- Security triage evidence on PR #31 HEAD `f11d696`, GitHub job `118914182878`: pip-audit found eight CVEs in Pillow 12.3.0 (CVE-2026-112895, CVE-2026-112400, CVE-2026-112397, CVE-2026-112896, CVE-2026-112897, CVE-2026-112395, CVE-2026-112404, CVE-2026-112899); fixed version reported as 13.0.0 for each. `mcias 0.1.0` skipped because not on PyPI; not a safety attestation. Security issue remains OPEN and independent; do not modify shared dependencies without owner coordination.
**Stop point:** documentation delivered for independent engineering review. No tests in this addendum executed, no implementation, no merge or deploy.
