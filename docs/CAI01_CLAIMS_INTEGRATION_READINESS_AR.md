# CAI-01 — Claims Audit Integration: Verified Baseline & Isolation Handoff

Date: 2026-10-21. Scope: read-only source/claim-batch preflight; **NOT production financial audit**.

## Verified GitHub source
- Repository: https://github.com/overurdream-collab/test2
- `main` baseline HEAD: `b69defa2f621458ef44d790b510840307a81009a`.
- Main checks on this SHA: G1–G7 / G8 / G9 / Enterprise completed SUCCESS (run G1–G7: https://github.com/overurdream-collab/test2/actions/runs/38179602026). Green CI is not financial accuracy or institutional acceptance.
- PR #20 A1 HEAD `6af41a0`, #23 Contract Intelligence `e0dd1d1`, #25 Inputs `8a616f7`, #29 Shared Audit `fd1bb1d`: all DRAFT/unmerged. PR #23 Documentation Governance/enforce FAIL on its checked SHA. Never import unapproved contract rates from draft.
- A1 has an independent fee/itemized adapter; do not reimplement. PR #29 owns Shared Audit Writer. PR #25 owns expanded input management. No files on these branches were edited.

## G2–G5 actual map
| Gate | Present on main | Gap |
|---|---|---|
| G2 | XLSX/CSV extraction, source locators, original SHA/encrypted storage, quarantine, coverage manifest | XLSX parser extracts **all** worksheets, source locator stores worksheet **index** not name; actual workbook not available; medical OCR accuracy not accepted |
| G3 | dated approved contract lookup, provider tariff, category, dated beneficiary enrollment | no verified historical family membership, individualized coverage matrix or itemized approved unit tariff in main |
| G4 | strict seven-column normalization, immutable source-linked entries, resumable chunks, row rejection, tenant isolation | no approved Arabic header mapper, worksheet semantic selector, normalized quantity/unit price/net/cost-share/family links; rejected-row status not persistently indexed per row |
| G5 | eight advisory checks, Decimal engine, signed policy grant checks, Palermo-2, immutable snapshot | no batch-wide production orchestration; read-only snapshot HTTP; caps/exclusions/cost-share checks merely test policy.approved in inspect_claim; clinical/frequency/provider statistical rules missing |

## Readiness matrix (implemented means the *specific claimed capability*, not just a named agent)
| Requested check | Grade | Evidence and limitation |
|---|---|---|
| 1 Same/different batch duplicates | PARTIAL | `mcias/audit_agents.py` checks same `claim_reference` in same organization across entries, not semantic invoice/line duplicates |
| 2 Contract tariff overbilling | PARTIAL | approved dated contract and matching G3 tariff, policy tariff equality only on calculable paths; lacks validated item/unit/quantity fee contract |
| 3 Cost-sharing accuracy | PARTIAL | Decimal copay per explicit policy; does not resolve member/date/category-specific cost share from G3 |
| 4 Eligibility, category, coverage | PARTIAL | dated enrollment and contract checked; class/service coverage absent |
| 5 Per-person/family/service caps | PARTIAL | policy scalar cap on one evaluation; not cross-claim/family ledger |
| 6 Invoice/procedure splitting | MISSING | no multi-claim splitting correlation logic |
| 7 Unusual frequencies/quantities | MISSING | G4 quantity not normalized; no benchmarks/rules |
| 8 Chronic medication recurring vs anomaly | MISSING | no duration/regimen or clinical evidence policy |
| 9 Medical contradictions | MISSING | no clinical decision evidence/rule |
| 10 Provider outlier patterns | MISSING | no cohort-normalized provider analytics |

All advanced checks are NOT_TESTED for institutional accuracy (no real golden reference corpus). Some basic synthetic components are covered by CI, not the requested full scenarios.

## High-impact risk order
1. **P0** Source-scope/coverage: treating XLSX summary/payment rows as new claims or silently omitting selected rows; do not assume sheet names or contents by index.
2. **P0** Historical member-specific tariffs, quantity, unit prices, required references, submitted member share vs expected calculation.
3. **P0** Historical individual/family/shared cap usage and ledger double counting, with no change to old decisions.
4. **P1** Cross-batch semantic duplicate candidates, invoice fragmentation, frequency patterning.
5. **P1** Evidence-gated clinical/chronic-medication and provider outlier indicators, always for HUMAN_REVIEW.

## Isolated proof-of-scope (this branch)
- `mcias/claims_batch_preflight.py` is pure/read-only and only consumes G2 `ExtractedSourceRecord` objects; no database writes, API, policy changes, engine, or new audit writer.
- XLSX requires explicit worksheet indexes from caller. **No institutional attestation of that selection is implemented**; the preflight cannot authorize its own mapping.
- Reports exact source/included/excluded/unscoped/ready/invalid counts, opaque G2 IDs and locators; malformed source/unknown selection/count mismatch block. Same service/amount/member produces only **POTENTIAL** duplicates for review, never an automatic deduction.
- Synthetic XLSX with 3 sheets (Claims Details 2 rows, Payment 1, Family Summary 1): 4 extracted, 2 in scope, 2 excluded, 2 ready, one potential duplicate pair, zero financial verdicts.
- Local disposable Python pytest `tests/test_cai01_batch_preflight.py`: 12 PASS, using local copy of matching baseline normalization/G2 parser. The authoritative repo CI for commit SHA must be checked separately.
- 2,000-row synthetic list only proves accounting/in-memory iteration, not throughput SLA, persistence, interruption recovery, or multi-batch scalability.

## Integration contracts and STOP
G4 `stage/resume` currently processes *every* extracted record in the G2 job. This preflight does **not** change that! Do not call `stage` for arbitrary multi-sheet files until an independently reviewed source-sheet mapping, provenance signature and tenant-bound selection contract are established, plus a coordinated G4 schema/API change. Need AI CTO coordination with #25 and A1.

G5 `run_audit` internally requires verified institution policy registry/grant and does not expose a write API; no batch-level G4→G5 pipeline or payable approved here. E2E from original Excel through G5 is **BLOCKED**, not PASS. Record-to-source G2→preflight only validated synthetically.

Next engineering slice after supervisor contract: trusted versioned XLSX column+sheet mapping incl. sheet identity/source SHA and per-row persisted outcome reconciliation; integrate with existing G4 only after coordination. Follow with G3 member/family/date tariff semantics and a synthetic fully authorized G5 batch journey. No merge/deployment/migrations without human governance.

## Files, tests, risks, rollback
Files added only: `mcias/claims_batch_preflight.py`, `tests/test_cai01_batch_preflight.py`, this report and DG-001 journal/current state files. Tests: local 12 PASS, GitHub Actions on PR HEAD PENDING at initial commit. Risk: worksheet index may change on workbook edit; source original SHA binding and approval are *not provided* by the read-only utility. Never interpret duplicates or selected sheet as certified. Rollback: leave isolated branch/PR unmerged; delete no history.
