# External test report template

Document ID: `MCIAS-EXT-002` · Version: 1.0 · Status: Draft for review · Language: English

[النسخة العربية](EXTERNAL_TEST_REPORT_TEMPLATE.md) · [Package index](ACCEPTANCE_PACK_INDEX_EN.md)

## Report identity

This is an **unfilled template**. All external outcomes are NOT_EXECUTED; no acceptance signatures exist. Copy into institutional storage and bind to EXTERNAL_TEST_PLAN. Both languages use identical identifiers; the institution resolves any conflict rather than assuming a legally binding translation.

| Field | Initial value |
|---|---|
| Report/institution/approved host | NOT_RECORDED |
| Full SHA/package hash/trust source | NOT_RECORDED |
| OS/Python/PostgreSQL/Node/Chromium/dependencies/images | NOT_RECORDED |
| Actual/expected Alembic head | NOT_RECORDED / 0019_reference_dataset_v1 |
| UTC window/operator/reviewer | NOT_RECORDED |
| Data class/authority reference/test databases | SYNTHETIC_PLANNED / NOT_RECORDED |
| Approved RPO/RTO/workload/concurrency/P95 | NOT_APPROVED |

## Outcomes

| ID | Scenario/sanitized command | Actual result | Internal evidence/hash | Defect/retest | Reviewer |
|---|---|---|---|---|---|
| EXT-01 | Per plan | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-02 | Per plan | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-03 | Per plan | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-04 | Per plan | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-05 | Per plan | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-06 | Per plan | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-07 | Per plan | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-08 | Per plan | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-09 | Per plan | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |
| EXT-10 | Per plan | NOT_EXECUTED | NOT_RECORDED | NOT_RECORDED | NOT_RECORDED |

PASS requires executed, evidenced success; FAIL is an executed wrong result; BLOCKED is a missing entry condition/unavailable feature; NOT_EXECUTED means not run. SKIPPED is not a pass, and a financial screenshot alone does not validate a calculation.

## Counts and measurements

Python passed/failed/skipped: **NOT_MEASURED**. Separate Seed test: **NOT_EXECUTED**. JS passed/failed: **NOT_MEASURED**. Browser routes/page errors/WCAG violations: **NOT_MEASURED**. Workflow/job identities, CI links and per-run SHA: **NOT_RECORDED**. Do not sum repeated suites; explain each skip/warning.

P50/P95/P99, throughput, CPU/RAM/IO, data volume, concurrency, warmup/duration: **NOT_MEASURED**. Clock source, samples and approved SLA: **NOT_RECORDED**. Restore time/data loss/BLOB hashes: **NOT_MEASURED**. Source/claim/evidence/snapshot/report reconciliation: **NOT_EXECUTED**.

## Defects and exceptions

Each defect records ID, severity, role/precondition, synthetic reproduction steps, expected/actual, financial/privacy impact, sanitized evidence, owner, fix SHA, retest, residual risk and reviewer. An institutional waiver cannot erase a mandatory acceptance-contract condition; resolve the requirement first.

## Signoff and handoff

Test lead/date: **NOT_SIGNED**. Independent financial reviewer/date: **NOT_SIGNED**. Security/privacy: **NOT_SIGNED**. Gate-acceptance authority: **NOT_SIGNED**. Accepted gates: **NONE_RECORDED**. Final disposition: **NOT_ISSUED**. Open blockers: **NOT_REVIEWED**. Subsequent production activation authority reference: **NOT_ISSUED**.

Never attach medical evidence, keys/account secrets or live-fixture files. Keep them internally under restricted custody/hashes; public reports contain sanitized references only. GATE_STATUS cannot become ACCEPTED without per-gate evidence and signatures.
