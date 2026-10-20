# C34 — isolated source-literal recall experiment (2026-10-20)

**Status:** IMPLEMENTED_PENDING_CI; do not claim real recall improvement until exact-SHA Qwen generation completes. Draft PR #23 ONLY. No merge, deploy, G3/G5 tariff activation, A1 or Document Reader changes.

## C33 factual baseline (frozen data and strict validator)
Source PR23 SHA `30a902f6bf0c1791cc1e80731adac565e1e79984`. [Actual Qwen C33 #39142051824](https://github.com/overurdream-collab/test2/actions/runs/39142051824): pinned Qwen/Qwen2.5-1.5B-Instruct revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, constrained JSON, TP2 FP0 FN4 / recall 33.33%, 7 actual generated calls, elapsed 683.0 seconds. Positive Arabic R1=3450 and English R2=910 both PASS. One injection negative quarantined (FP0).

Raw C33 outputs vs unchanged `validate_candidates`:
- R3 CONSULT 4100: model `rule_type=duration`, `currency=null`, `amount=null`, key literal `provider_code:service_code`. Reject `tariff_identity_incomplete`; no supported tariff price candidate.
- R4 XRAY 8200: `service_code="XRAY 8200"`, `logical_key="R4:XRAY 8200"`, `amount="150000"`. Reject `invalid_service`, `invalid_logical_key`, `tariff_identity_incomplete`, `numeric_not_in_source`; original 8200 must remain only valid source amount.
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
