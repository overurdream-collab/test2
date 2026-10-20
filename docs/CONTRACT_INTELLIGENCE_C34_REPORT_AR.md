# C34 — isolated source-literal recall experiment (2026-10-20)

**Status:** IMPLEMENTED_PENDING_CI; do not claim real recall improvement until exact-SHA Qwen generation completes. Draft PR #23 ONLY. No merge, deploy, G3/G5 tariff activation, A1 or Document Reader changes.

## C33 factual baseline (frozen data and strict validator)
Source PR23 SHA `30a902f6bf0c1791cc1e80731adac565e1e79984`. [Actual Qwen C33 #39142051824](https://github.com/overurdream-collab/test2/actions/runs/39142051824): pinned Qwen/Qwen2.5-1.5B-Instruct revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, constrained JSON, TP2 FP0 FN4 / recall 33.33%, 7 actual generated calls, elapsed 683.0 seconds. Positive Arabic R1=3450 and English R2=910 both PASS. One injection negative quarantined (FP0).

Raw C33 outputs vs unchanged `validate_candidates`:
- R3 CONSULT 4100: model `rule_type=duration`, `currency=null`, `amount=null`, key literal `provider_code:service_code`. Reject `tariff_identity_incomplete`; no supported tariff price candidate.
- R4 XRAY 8200: `service_code="XRAY 8200"`, `logical_key="R4:XRAY 8200"`, `amount="150000"`. Reject `invalid_service`, `invalid_logical_key`, `numeric_not_in_source` (the malformed logical key still equals malformed provider+service, so it does NOT emit `tariff_identity_incomplete`); original 8200 remains only valid source price.
- R5 MRI 12000: source XLSX field `price="12000"`; model quote `12000 YER` crosses fields, reject `quote_not_in_source`.
- R6 LAB 650: source XLSX field `price="650.00"`; model quote `LAB 650.00 YER 2026-01-01 2027-01-01` crosses fields, reject `quote_not_in_source`.
- Source quote must be verbatim within ONE field; other XLSX identities/dates may be verified in the SAME G2 row. Raw output diagnostics and negative replays are not accepted candidates.

## C34 minimal candidate
One opt-in boolean `benchmark_tariff_literals` in `infer_local`, default FALSE, changes only the explicit isolated benchmark system text, with no price/code example or gold-based mapping: (a) distinguish provider/service/price/currency/date and priced clause vs duration; (b) never absorb price digits into service; (c) for sheet rows quote exactly one source field, not synthesized multi-cell quote. No changes to `validate_candidates`, scoring/gold, model revision, source SHA/locator, production default prompt, approval, DB, reference rules or tariff money paths. `--diagnostic-tariff-literals` explicitly opts benchmark in. Reports now include per-candidate raw synthetic model output and validator error/status for independent reinspection.

## Acceptance plan and reproducibility
- Original C33 corpus **unchanged**, including R1/R2 and negative. C34 candidate: `python scripts/contract_ai_benchmark.py --split-multi-tariff --diagnostic-tariff-literals --cases-file tests/fixtures/contract_independent_synthetic.json --output /tmp/c34-c33.json`.
- Distinct prospective synthetic holdout with independently authored 6 true positive clauses and injection negative, `tests/fixtures/contract_c34_holdout_synthetic.json`. It is a *separate* sample, not production or a statistical generalization claim.
- Each matrix job pins the same real Qwen model/decode/runtime as C33, runs C33 raw-rejection deterministic replay and negative validation tests first, and uploads hashed inference and literal rejection trace. Compare TP/FP/FN/Recall and seconds vs baseline; source anchors, no newly accepted negative, and retained R1/R2 required. No fabricated or substituted candidate values.
- C33 baseline: TP2 FP0 FN4 recall33.33%, 683s. C34-C33: PENDING REAL MODEL. C34 holdout: PENDING REAL MODEL (no identical historical baseline, report absolute metrics only or run matched baseline separately). Original C33 run measures first model start and warmup; latency is descriptive, not statistically controlled.
- C34 CI links: must be filled from actual GitHub workflow run, never inferred or claimed in advance. All reference CI pending on new SHA; no merge or deployment.

## DG-001 HANDOFF
STATUS=IMPLEMENTED_PENDING_CI; SCOPE=isolated test-only model guidance; BASE=30a902f6bf0c1791cc1e80731adac565e1e79984; OWNER=PR23 Contract Intelligence; SOURCE=GitHub C33 log + unmodified fixture and validator; TESTS=run C34 unit/replay and real-model matrix + reference CI; RISK=low actual recall, model variability, tiny synthetic set, forced nonempty even negative, model weights download; NEXT=inspect latest exact-SHA run artifacts and compare candidate vs baseline without altering validator; NO FINANCIAL AUTHORITY.

## C34 workflow visibility note
Initial source commit `b1ecee68bcb240cd72e685c3565c7a21b534279c` used push-only C34 workflow; because the GitHub PR-run inspection interface does not expose push-only workflows, a subsequent atomic DG-001 commit adds a PR trigger. New C34 metrics remain PENDING_CI until the two PR matrix jobs finish; old C33 values are baseline only.

### C34 first attempted run — TEST EXPECTATION FAILURE
- Source `f18cd41062ac805eabe5e9cabae04e826c0feec8`, [C34 matrix run 39481536110](https://github.com/overurdream-collab/test2/actions/runs/39481536110): both jobs **FAIL before model generation** at added frozen-output test; 1 failed / 7 passed in each. Test incorrectly demanded `tariff_identity_incomplete` for R4, but unchanged validator correctly returned precisely `invalid_service`, `invalid_logical_key`, `numeric_not_in_source` since its malformed key equals malformed `provider:service`. This is not a model-quality result. Retain all three independent rejection assertions. Repair expected codes only; do not change validator/source/Gold or remove test. Real C34 results still PENDING_CI.

## C34 — FINAL MEASURED FINDING (2026-10-20): REJECT CANDIDATE
**Exact source-code SHA:** `16cc288e8c71eeb5731f36fe39a16e617e6f3483`. The workflow itself succeeded as **execution**, but the C34 experimental prompt **FAILED quality**. No claim of recall improvement, no release, no activation; the benchmark-only switch remains OFF by default in the production caller.

| Run / dataset | TP | FP | FN | Recall | Total elapsed |
|---|---:|---:|---:|---:|---:|
| Historical C33 [39142051824](https://github.com/overurdream-collab/test2/actions/runs/39142051824) | 2 | 0 | 4 | 33.33% | 683.0s |
| Same-SHA C33 unchanged prompt [39481874804](https://github.com/overurdream-collab/test2/actions/runs/39481874804) | 2 | 0 | 4 | 33.33% | 410.2s |
| C34 opt-in prompt on **unchanged C33 corpus** [39481874549](https://github.com/overurdream-collab/test2/actions/runs/39481874549) | **1** | **0** | **5** | **16.67%** | **819.8s** |
| C34 opt-in prompt on **separate C34 holdout** [39481874549](https://github.com/overurdream-collab/test2/actions/runs/39481874549) | **2** | **0** | **4** | **33.33%** | **829.1s** |

The frozen-C33 candidate **lost 1 true positive (R2)**; recall fell by 16.67 percentage points, no FP increase. Same-SHA wall-clock took ~409.6s longer, but shared CI runner variance/model caching prevents a controlled performance attribution. Holdout has different data/gold, so its 33.33% is **not** a before/after recall improvement. Both C34 matrix jobs PASS their execution and negative gates; do **NOT** interpret green Actions as a quality pass.

### Actual C34 generated candidates and independent rejection reasons (not guessed)
Frozen original C33:
- R1 Arabic: **TP**, valid `R1:CONSULT 3450`, no validation errors.
- R2 English: **FN**, generated key `r2-xray`, reject `tariff_identity_incomplete`; legitimate source amount 910.00 is not enough to override unsupported key.
- R3 provider: **FN**, generated price `4100` but empty currency, errors `invalid_currency`, `tariff_identity_incomplete`.
- R4 provider: **FN**, `service_code="XRAY 8200"`, empty currency, unsupported `amount="500"`; `invalid_currency`, `invalid_service`, `numeric_not_in_source`, `tariff_identity_incomplete`.
- R5 Excel: **FN**, quote `12000 YER` is not a literal single cell; `quote_not_in_source`.
- R6 Excel: **FN**, fabricated amount `950.00` against source `650.00` and quote `650.00 YER` not one cell; `numeric_not_in_source`, `quote_not_in_source`, `tariff_identity_incomplete`.
- Negative transfer: no accepted tariff; `missing_effective_from`, `tariff_identity_incomplete`.

Separate holdout (independently authored synthetic six-positive/one-negative):
- Arabic T1 LAB 2750 and second provider T4 CONSULT 9300 **TP2**.
- English T2 MRI 730 key `t2-mri` rejected: `tariff_identity_incomplete`.
- T3 XRAY 4600 malformed code rejected: `invalid_logical_key`, `invalid_service`.
- Sheet T5 `15250 YER` rejected `quote_not_in_source`; Sheet T6 `890.00 YER` rejected `quote_not_in_source`, `tariff_identity_incomplete`.
- Negative transfer quarantined: `invalid_service`, `missing_effective_from`, `tariff_identity_incomplete`; **FP0**.

### CI and earlier failure preservation
- Actual C34 [39481536110](https://github.com/overurdream-collab/test2/actions/runs/39481536110) **FAILED before model inference**: original replay test asserted an extra R4 error; corrected without touching validation; keep failure in history.
- Final [C34 39481874549](https://github.com/overurdream-collab/test2/actions/runs/39481874549): two jobs execution PASS, deterministic replay PASS and actual model outputs as above, **QUALITY REJECTED**.
- Original C33 [39481874804](https://github.com/overurdream-collab/test2/actions/runs/39481874804) execution PASS; independent original [39481874799](https://github.com/overurdream-collab/test2/actions/runs/39481874799) execution PASS; source-specific [39481874731](https://github.com/overurdream-collab/test2/actions/runs/39481874731) execution PASS.
- Required [DG-001 39481875094](https://github.com/overurdream-collab/test2/actions/runs/39481875094), [G1–G7 39481875224](https://github.com/overurdream-collab/test2/actions/runs/39481875224), [G8 39481874607](https://github.com/overurdream-collab/test2/actions/runs/39481874607), [G9 39481874512](https://github.com/overurdream-collab/test2/actions/runs/39481874512), [Enterprise 39481874567](https://github.com/overurdream-collab/test2/actions/runs/39481874567), [LMFE 39481875065](https://github.com/overurdream-collab/test2/actions/runs/39481875065), [Decimal 39481874730](https://github.com/overurdream-collab/test2/actions/runs/39481874730) all execution PASS on source-code SHA `16cc288e8c71eeb5731f36fe39a16e617e6f3483`.

### Decision and next controlled experiment
**REJECT C34 prompt as a quality improvement; do not enable it for applications**. Existing `infer_local` default prompt is byte-for-byte unchanged and C33 successes remain preserved in the default path. Do not use bench opt-in flag to import or approve a tariff. Separate next proposal requires supervised research into model's structured quote/field reliability and explicit source-evidence fidelity, with unchanged strict validator and independent corpus; no autopatching or Gold changes in C34. The small synthetic metrics do not establish real insurance contract clause extraction.
