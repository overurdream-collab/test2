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

## 9. Mandatory INPUTS-FIRST audit policy — owner directive 2026-10-21
**Governance status:** Binding design/acceptance requirement, **not evidence that all six reference families are implemented or populated**.
- Every imported claim/line must carry `organization_id`, source-row provenance, service date, `reference_snapshot_id`, effective-dated approved reference IDs/versions and audit plan/rule versions, with per-check `PASS | CONFIRMED_FINDING | NEEDS_EVIDENCE | UNABLE_TO_AUDIT`. A missing reference or unresolved contradiction must not silently become PASS.
- Required six reference families: (1) beneficiary identity, employee/family membership, per-person class/coverage and dates; (2) approved contracts and provider terms/exclusions; (3) provider/contract/class/date-specific tariffs; (4) medical, administrative and financial policies/authorization; (5) benefit caps and cumulative consumption; (6) historical claims/dispensing and recurrence/chronic medication context. The audit snapshot must distinguish `reference_missing`, `reference_unapproved`, `reference_not_effective`, `reference_conflict`, and `reference_proven_violation`.
- All claims are included in coverage/reconciliation. No sampled subset may be reported as full audit. Incomplete required checks remain `MISSING_EVIDENCE` or `UNABLE_TO_AUDIT` with review routing; no auto approval. A missing beneficiary in an incomplete source is **not** confirmed ineligibility.
- Existing G5 must remain the audit engine. Extend only via reviewed shared contracts: tariff discrepancy, duplicate services/invoices, cap and historical use, chronic/refill timing, diagnosis-treatment-medication-test consistency, coverage/exclusions, possible unperformed service **requiring independent proof**, identity/provider/date mismatches, splitting to evade limits, arithmetic/admin errors. Suspicion is a review signal, not a proven financial rejection.
- Proven violation requires trusted original evidence, reference version and effective period, observed/reference values, claim and affected amount/currency, rule ID/version, impact, audit event, human authorization for final financial disposition. Financial approval is a separate dimension from audit classification; no model may override institutional inputs.
- Scale target is **up to 200 million in total claimed monetary value over two months**, not 200 million rows. Capacity planning must derive actual row counts, claim-line cardinality, historical lookback, source sizes and service-level targets from measured datasets; batch/keyset import, resumable checkpoints, idempotency, tenant isolation and complete reconciliation remain prerequisites.
- Dependencies/ownership: G3 owns effective-dated references and source completeness attestations; A1 invoice/medical evidence integrity; Contract Intelligence extracts candidates but cannot activate clauses without approval; Document Reader supplies source-linked OCR evidence not financial truth; G2 source manifest; G4 imports eligible rows; G5 deterministic checks; G6 human decisions; G7 coverage/risk reporting; G8 independent validation; PR #25 unified inputs; PR #29 Shared Audit immutable evidence/events. All require independent integration review before shared edits.
- **Status:** G2 Excel locator and G4 stage/resume and isolated CAI-01 preflight exist, but full six-family approved reference binding, source completeness, historical cross-batch G5 execution, clinical checks, comprehensive end-to-end verification and production throughput are **not proven**. No new engine, no financial decision automation, no shared change authorized by this addendum.

## 10. Phase 3 controlled verification evidence and stop gates (2026-10-21)
**Verified HEAD before work:** `4ed7c4c67cc5eb7fe6ea39d5178ee69579fbcd8e`. GitHub Actions Run `39506569513`: unit SUCCESS (job 118916862510), postgres-integration SUCCESS (job 118916862472), dependency-audit FAILURE (job 118916862108). These existing green checks are **not** the required multi-batch Excel → G4 → G5 acceptance.
**Executed in isolated local CAI-01 sandbox:** `PYTHONPATH=. python -m pytest -q tests/test_cai01_batch_preflight.py` → **12 passed in 0.46s**, no skips/fails. An initial direct `pytest -q` invocation failed during collection (`ModuleNotFoundError: mcias`), resolved by invoking via `python -m pytest` with `PYTHONPATH=.`; no code was modified. This tests read-only preflight only; **not** PostgreSQL/G4/G5 end-to-end.
**Environment limitation:** local runtime has no `psql`, `postgres`, `pg_ctl` or Docker command available; `psycopg` not installed. No PostgreSQL 16 test instance, database connection or real multi-batch execution established. Do not misrepresent existing CI PostgreSQL pass as a Phase 3 acceptance run.

### Phase 3 verification matrix — actual evidence, not inferred
| Required assertion | Phase 3 verified? | Blocker |
|---|---|---|
| Original Excel file SHA, sheet name/type, physical row provenance | NO | G2 locator lacks attested worksheet name/type and full physical-row ledger |
| Exclude PAYMENT/FAMILY_SUMMARY and exact financial/date/currency reconciliation | NO end-to-end | Existing preflight is read-only; approved sheet manifest not enforced in G4 |
| G4 → G5 eligible-only source rows | NO | G4 stages all extracted rows; no approved-row filter |
| Beneficiary/employee/dependent effective-dated reference checks | NO | G3 approved versioned reference snapshot and fixture binding not demonstrated |
| Tariff/provider/contract/version, copay, caps, cumulative history | NO | shared G3/G5 integration and double-count-safe ledger unverified |
| Intra/inter-batch semantic duplicate, restart, tenant isolation | NO end-to-end | PostgreSQL 16 multi-batch controlled run not executed |
| Chronic refill, clinical conflicts, suspicious unperformed service, valid negatives | NO | approved rules/evidence and G5 evaluation fixtures not executed |
| Claim/line TP FP FN Precision Recall | NOT MEASURABLE | no executed labeled E2E outcomes; no invented scores |
| Rows/sec, RSS, import/check time, resume time, SQL cumulative query cost | NOT MEASURED | no PostgreSQL 16 end-to-end/load run |
| Existing isolated source preflight unit tests | YES, 12/12 local | narrower than Phase 3 acceptance |
| Shared dependency security audit | FAIL | Pillow 12.3.0 eight CVEs; security owner coordination needed |

### Acceptance data accounting (not yet collected)
- Number of Phase 3 PostgreSQL 16 executed batches: **0**; actual source worksheets: **0**; actual accepted/excluded/held/imported row totals: **NOT MEASURED**; no claim of zero defects.
- Synthetic scenarios remain specified in sections 7–9 but unexecuted as an integrated chain. No approved clinical policy or institutional death source may be fabricated for test acceptance.
- The absence of production-scale measurements is not proof of poor or good throughput; 200 million is monetary claim value, not row count.
- Required next authorized step: provide a runnable PostgreSQL 16 isolated CI workflow or compatible test environment and approve narrowly scoped G2 provenance / G4 approved-row import contract changes with respective owners. Then execute four-batch fixtures, capture immutable run IDs/artifacts, SQL and RSS metrics, claim/line confusion matrix and reconciliation before any readiness change.
**Integration readiness decision: BLOCKED / NOT VERIFIED.** No shared code changes, merge, deployment, financial decisions, or dependency bypass performed.

## 11. INPUTS-FIRST integration supervision / independent contract acceptance plan (2026-10-21)
**Baseline verified:** PR #31 HEAD `5b391dba376fade78f4727f6e171f608badb2dd0`, Draft/unmerged. CI run `39507129932` at inspection: unit and postgres-integration IN_PROGRESS, dependency-audit FAILURE (job `118918751659`). Do not report in-progress checks as passed. Failure log again confirms Pillow 12.3.0 with eight CVEs, fixed-version 13.0.0 per pip-audit; `mcias 0.1.0` unaudited/not PyPI.
**Six-reference contract acceptance:** each *applicable* check must bind approved source authority, reference ID/version, effective-from/to including service date, source completeness attestation for query scope, rule ID/version, claim/line ID, raw evidence pointer, normalized value, decision/finding event and check disposition. Reference families: beneficiary/employee/dependents; contract/coverage; provider tariff; policies/authorization; cap/consumption; history/previous claims. `NOT_APPLICABLE` requires recorded reason and rule; absent/unapproved/out-of-period/incomplete references yield `MISSING_EVIDENCE`/`UNABLE_TO_AUDIT`, not confirmed violation.
**Audit-state crosswalk:** four supervisory states are semantic evaluation states, not a replacement for five dashboard classifications: `PROVEN_MATCH` requires every mandatory applicable check completed without finding; `PROVEN_VIOLATION` requires authenticated dated evidence and approved rule; `UNRESOLVED_OR_MISSING` routes HUMAN_REVIEW/MISSING_EVIDENCE; `UNABLE_TO_AUDIT` stays outside completed denominator. Human-approved rejection is a separate event-backed projection, not an automated decision. Financial approval is independently displayed.
**Verified existing functionality:** G2 openpyxl read-only extractor with sheet-index/physical-row locator; CAI-01 `inspect_extracted_records` read-only explicit selected claim sheet indexes and row validation; G4 `stage`/`preview`/`resume` with actor organization guard, extraction completeness and source SHA; existing G5 audit engine is sole audit owner. These facts do not establish approved sheet type, row-level full coverage or G3 versioned reference binding.
**Unimplemented or unproven handoff:** G2 original worksheet name/type + raw/normalized source ledger; trusted reviewer-approved manifest and completeness; G4 presently counts/stages all extracted rows and does not require trusted claim-only manifest; G5 applicable-check six-family snapshot and completeness not demonstrated; Shared Audit append-only event integration and human approval cross-branch contracts not demonstrated. Weak OCR cannot prove a violation, and suspicious unperformed service requires independent verification.
**Ten-case synthetic acceptance matrix (planned; no execution):**
| Case | Input | Expected supervisory outcome | Required proof |
|---|---|---|---|
| T01 | valid claim, all applicable refs complete | PROVEN_MATCH | six-family applicable check coverage, original/normalized amounts |
| T02 | beneficiary absent from incomplete list | UNRESOLVED_OR_MISSING | completeness=false, no ineligibility finding |
| T03 | confirmed duplicate invoice/line | PROVEN_VIOLATION only with approved duplicate rule; otherwise review | same-tenant history, source keys, no double count |
| T04 | provider-specific tariff exceeded | PROVEN_VIOLATION only with approved tariff policy | effective contract/tariff, amount/currency |
| T05 | cap overrun | PROVEN_VIOLATION only with approved cap policy | prior usage excluding current claim, limit period |
| T06 | possible early chronic refill | UNRESOLVED_OR_MISSING pending approved schedule/policy | dispensing history, days-supply and dates |
| T07 | diagnosis/service contradiction | HUMAN_REVIEW | A1/reader evidence, clinical expert review |
| T08 | possibly unperformed service, no independent proof | HUMAN_REVIEW | suspicion indicator explicitly not proven |
| T09 | unreadable source/OCR without reliable field locator | UNABLE_TO_AUDIT | source error, no fabricated evidence |
| T10 | reference expired before service date | UNRESOLVED_OR_MISSING | effective date failure, search for correct historical version |
Acceptance: no unauthorized row to G4, original value retained, source-to-audit traceability, no cross-tenant access, no false proven finding from missing source, all ten tests executed with claim/line TP/FP/FN before sign-off; report missing/not-applicable counts separately.
**Non-duplicating ownership and requested decisions:** G2 owns raw provenance/classification inventory; G3 owns approved dated reference snapshots and completeness; G4 owns approved-row gate/idempotent import; G5 owns deterministic tariff/cap/duplicate/copay and finding projection; Shared Audit PR #29 owns event schema/writer; A1 owns invoice integrity; Document Reader owns OCR source-located evidence; Contract Intelligence owns candidate clause extraction with human approval; G6 human authorization; G7 dashboard; G8 independent acceptance. AI CTO/project owner must approve manifest authority, shared event schema, reference-completeness semantics, G4 gate, rule versions and security dependency owner before any code integration. Coordinate security-only Pillow 13.0.0 compatibility test on dependency owner's branch; no CAI-01 shared dependency edits.
**Readiness:** contract verification/planning ONLY; end-to-end acceptance PENDING. No new PostgreSQL 16 integrated run, measured precision/recall or throughput from this review. No merge/deploy/financial decisions.

## 12. INPUTS-FIRST isolated verification implementation (2026-10-21)
- Baseline HEAD `ea7636acd308ad326f4f0f18ab7636d8c154629a`, PR #31 Draft. CI Run `39507267717`: unit SUCCESS, postgres-integration SUCCESS, dependency-audit FAILURE. Job `118919221056` confirms Pillow 12.3.0 eight CVEs and pip-audit 13.0.0 fix; local mcias 0.1.0 not audited by PyPI.
- Added `tests/test_cai01_inputs_first_source_contract.py` with ten synthetic **source/preflight** assertions: missing sheet approval, non-claim exclusions, unknown sheet, invalid amount, incomplete source count, duplicate locator, semantic duplicate review, valid source not financial approval, invalid date, invalid currency. These tests deliberately do not mock a G5 decision or claim to verify six reference families. New CI execution result must be checked on this commit before calling tests PASS.
- **Ten requested G4/G5/Shared Audit acceptance scenarios:** T01 valid claim BLOCKED; T02 beneficiary missing/incomplete reference BLOCKED; T03 duplicate BLOCKED (source-only candidate test exists); T04 tariff BLOCKED; T05 cap BLOCKED; T06 periodic dispensing BLOCKED; T07 clinical conflict BLOCKED; T08 unperformed-service suspicion BLOCKED; T09 OCR failure BLOCKED; T10 expired reference BLOCKED. All are BLOCKED **for end-to-end acceptance** pending real PostgreSQL 16 G4/G5/Shared Audit and approved G3 data; none are claimed as passing from preflight.
- **Measured E2E:** 0 completed PostgreSQL 16 four-batch acceptance runs, no proven raw+normalized provenance coverage percentage, no applicable-reference coverage, no Shared Audit event transmission metrics. These values are NOT MEASURED, not zero percent.
- G2 owner: approved worksheet name/type, physical row coverage, raw+normalized values. G3 owner: effective-dated six-family reference completeness. G4 owner: server-side trusted eligible-only manifest gate. G5 owner: check coverage, deterministic rules and evidence outcomes. Shared Audit PR #29 owner: immutable event contract. AI CTO approval required before shared changes.
- No parallel parser/importer/engine/audit writer, no shared code modifications, no merge/deploy/financial decisions. Integration acceptance PENDING.
