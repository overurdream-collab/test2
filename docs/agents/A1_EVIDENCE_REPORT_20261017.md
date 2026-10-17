# A1 — Synthetic engineering evidence report (2026-10-17)

**DECISION: NOT ACCEPTED / Draft PR only.**
This is a technical trial, not a claim-rejection engine or institutional fraud finding.

## Baseline and scope

Main: b69defa2f621458ef44d790b510840307a81009a.
Master design: PR #19 (unmerged).
A1 code: mcias/agents/invoice_integrity.py.
No modified claims, approved tariffs, G5 financial snapshots, databases, G6/G7/G8,
or production deployment. Original G5 regression CI remained green at
https://github.com/overurdream-collab/test2/actions/runs/39049022307.

## Hand-authored reference cases and deterministic measurement

Source: tests/a1/synthetic_cases.py, 18 labeled, reproducible synthetic bundles.
Runner: python -m scripts.evaluate_a1 --output a1-results.json.
Evidence: https://github.com/overurdream-collab/test2/actions/runs/39048517128

Observed (rules only, first clean CI run): 35 targeted pytest cases passed,
TP=7, FP=0, FN=0, TN=2, 9 abstentions (INSUFFICIENT_EVIDENCE).
Precision=7/(7+0)=1.0, Recall=7/(7+0)=1.0 **on this small curated set**.
Mean per-bundle deterministic latency=0.0863ms, p95=0.1267ms, peak Python RSS
19,800KiB, peak-RSS change 144KiB (Linux CI). No OCR, DB, LLM, startup or I/O
in this benchmark. Later changes may increase regression test count; use the
latest CI logs for final counts.

Examples (synthetic YER):
- Clean: LAB-A 2 tests × 10.0000, contract price 10.0000, attested quantity 2,
  invoice and claim 20.0000. PASS.
- Inflated unit rate: 2 × 15.2500 billed, allowed rate 10.0000.
  PRICE_OVERCHARGE REVIEW, advisory gap 10.5000 YER.
- Inflated quantity: billed 3 LAB-A tests, one attested record confirms 2.
  QUANTITY_MISMATCH REVIEW. Not an automatic deduction.
- Extra fee: unlisted fee 7 YER, approved fee schedule explicitly exhaustive.
  UNJUSTIFIED_FEE REVIEW; without exhaustive clause, abstain.
- Legitimate additional fee: contract explicitly permits ADMIN fee of 3 YER:
  PASS when invoice total=23.
- No record, OCR-only or missing unit: INSUFFICIENT_EVIDENCE, not a fabricated
  quantity verdict.
- At effective_until (exclusive): no active contract -> abstain.
- Currency mismatch / another tenant: no cross-currency conversion/tenant join.

## Actual open-weight inference — measured, not simulated

Official public weights: Qwen/Qwen3-0.6B-GGUF,
revision 23749fefcc72300e3a2ad315e1317431b06b590a,
file Qwen3-0.6B-Q8_0.gguf (639,446,688 bytes),
SHA-256 9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031.
Free GitHub-hosted CPU with in-process llama.cpp; input strictly synthetic,
no paid model API. Exact model ID and hash are recorded by the probe script.

Run 39048517128: two actual model invocations, raw generation occurred,
but both had MODEL_OUTPUT_INVALID due unstructured output; correctly not
treated as validated findings.

Run 39048790090: structured JSON constrained, two actual invocations,
both INFERRED_VALIDATED with zero proposed findings. Synthetic examples clean
and prompt injection; runtimes 2.2973 and 2.1754s, peak RSS 1,106,292 KiB.
https://github.com/overurdream-collab/test2/actions/runs/39048790090

Run 39048893187: three actual invocations testing agreement, attack and a
textual contradiction. All produced syntactically valid bounded JSON.
**Prior to the latest independent citation-relevance guard**, outcomes:
clean TN=1, injection FP=1, real contradiction FN=1, TP=0.
Thus measured *model suggestion* precision=0/(0+1)=0, recall=0/(0+1)=0
on three hand-constructed examples; NOT a large blind dataset.
Latencies: 2.7024s, 4.5404s, 2.9637s; peak RSS 1,109,516 KiB.
https://github.com/overurdream-collab/test2/actions/runs/39048893187

Following this failure, the experimental advisor rejects model quotations
that do not even contain an invoiced service code, and adds adversarial
regressions. This may suppress the unrelated injection-derived false alert,
but **does not prove the model can detect the missed contradiction**.
Consult latest head CI for re-run outcome. Old measurements are retained above,
not silently rewritten as success.

## Comparator limitation

The existing live G5 rule checker checks tariff existence and currency for
one service_code and uses policy-authorized Decimal aggregate claim
reconciliation. It does not receive this independently generated item-level
invoice/contract/unit dataset. A numeric apples-to-apples Precision/Recall
comparison to G5 is **NOT AVAILABLE**, pending an authorized trusted adapter
and common expert-adjudicated corpus. No fabricated baseline scores.

## Blocking items before technical acceptance

1. Small Qwen3-0.6B has **not** demonstrated acceptable semantic contradiction
   recognition (actual FN recorded). Evaluate Qwen3-8B or other suitable
   open-weight model on sufficiently resourced free environment.
2. Independent blinded gold labels, calibration, error costs and repetition.
3. Institution-authorized mapping for genuine invoice unit semantics, date-
   versioned tariffs and immutable raw source hashes: current G3/G4 is not a
   turnkey itemized adapter.
4. Palermo-2 extension for source and LLM citation checking, Professor OS,
   Gateway, G6 review and G7 savings integration; not deployed as part of A1.
5. Institutional policies, human approvals, security and production gates
   remain OPEN. No silent deployment or merge.

## Reproduction links

- Source: mcias/agents/invoice_integrity.py
- Synthetic cases: tests/a1/synthetic_cases.py
- Targeted tests: tests/test_a1_invoice_integrity.py
- Deterministic benchmark: scripts/evaluate_a1.py
- Real model probe: scripts/a1_probe_local_model.py
- Scoped CI: .github/workflows/a1-invoice-integrity.yml
- Design notes: docs/agents/A1_INVOICE_INTEGRITY.md
- Draft PR: https://github.com/overurdream-collab/test2/pull/20
