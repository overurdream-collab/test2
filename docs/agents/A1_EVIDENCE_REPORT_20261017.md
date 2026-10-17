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


---

## 2026-10-17 follow-up: TRUE Qwen3-8B, blinded-then-policy-hardened comparison

Do not overwrite the failure measurements above. They led to a necessary
*independent source-attestation guard*; a model-generated exact quote was
demonstrably insufficient to prove that a source was trusted.

**Actual model:** official Qwen/Qwen3-8B-GGUF Q4_K_M
- revision: 7c41481f57cb95916b40956ab2f0b139b296d974
- file: Qwen3-8B-Q4_K_M.gguf
- SHA256: d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785
- file size: 5,027,783,488 bytes
- model runs on GitHub's free public-repository Ubuntu CPU runner; no GPU paid
  endpoint and no patient claims or external inference service.

**Initial 8B development experiment**, source code before the source-attestation
guard: 10 synthetic samples, TP=2/FP=0/FN=0/TN=8, precision=1.0,
recall=1.0, mean 5.98529s per request and 9,255,344 KiB peak process
RSS. Raw generations and weight checksum in CI artifact:
https://github.com/overurdream-collab/test2/actions/runs/39050642975

**First 26-case holdout experiment (important FAILED qualification run)**:
TP=8, FP=2, FN=0, TN=16; precision 8/(8+2)=0.8, recall 8/(8+0)=1.0.
False positives were cases "bill_summary_only" (unverified billing note) and
"label_not_instruction" (injected instructions in text). Initial 10 cases
remained TP=2/FP=0/FN=0/TN=8. Total 36: TP=10, FP=2, FN=0, TN=24;
precision 10/12=0.8333, recall=1.0. Gate appropriately failed:
https://github.com/overurdream-collab/test2/actions/runs/39051176994

**Corrective design:** require a trusted attested source record and matching
service code, real source quote, explicit performed-service verb, quantity
literal contained in that quote, invoice line ID, and amount/quantity mismatch.
Independently record rejected model signals. Reject unverified OCR, copied
invoice notes, unsigned drafts and injected commands as evidence supporting
a REVIEW finding. This is a deterministic **evidence validation** layer,
not a substitute for LLM extraction from genuine service narratives.
Source attestation is supplied by the **trusted upstream snapshot provider**;
this standalone prototype cannot cryptographically prove it. No claim
rejections or deductions are generated.

Fixture source-attestation metadata was authored separately from labels:
trusted sources exist in both positive and negative scenarios.
Original positive/negative reference labels were **NOT changed**. Structured
quantity facts were removed from textual LLM fixtures so the positive signal
requires actual model text interpretation rather than reusing quantity rules.

**Post-fix evaluation** (note: this is a regression set previously inspected,
*not a second independent blind holdout*): 36 synthetic model invocations;
total TP=10/FP=0/FN=0/TN=26, precision=1.0, recall=1.0.
26-case subset: TP=8/FP=0/FN=0/TN=18.
Mean measured end-to-end per-case model inference 8.7753s; peak process
RSS 10,148,124 KiB (~9.68 GiB); 16 GB CPU runner.
The model is authentic and responses are recorded in CI artifacts.
https://github.com/overurdream-collab/test2/actions/runs/39051968767

**Post-fix deterministic tests**: 42 passed. Rules-only benchmark 18 cases:
TP=7/FP=0/FN=0/TN=2 and 9 abstentions; mean 0.1143ms/case, p95
0.1546ms/case, peak RSS 19,736 KiB (metrics exclude ingestion and I/O).
G1–G7 existing regression suite passed in GitHub Actions at the same
source-code head. Real LLM evaluation and rules evaluation are NOT conflated.

**Unresolved / MUST NOT CALL PRODUCTION-READY**:
- Expert-reviewed blind dataset from independent medical bill audit specialists
  with adjudication of contracts, OCR variance and multilingual bills. The
  synthetic result does NOT measure real-world PPV or sensitivity.
- The trusted G3/G4 itemized invoice/contract adapter must be built and
  unit semantics explicitly approved; no guessed unit prices. Current G5
  checkers are not a same-input line-item comparator, so no fabricated
  G5 Precision/Recall baseline is claimed.
- Attestation metadata and stored file SHA-256 must be independently verified
  by Palermo-1/2 against immutable input bytes; typed text quotes alone are
  not cryptographic proof. Integration deliberately outside A1 scope.
- Full institutional human-review gates, authorization, privacy and
  separate approval before any financial consequence or main merge.

**Disposition:** A1 is a functioning **synthetic-only proof of concept**
with REAL Qwen3-8B inference and validated code path, but is not institution-
accepted. The draft PR must remain unmerged. No A2 work performed.


---

## Existing G5 engine comparison — measured compatible six-case subset

A direct full-population metric is not honest because the existing G5 engine
has aggregate claim amounts but no common trusted item-level quantity/unit
mapping. An *actual* restricted common-input experiment was therefore run
against the unmodified existing \`mcias.audit_engine.evaluate\` with an
explicitly authorized-for-TEST synthetic per-claim tariff ceiling:

    python -m scripts.compare_a1_g5_baseline --output a1-g5-comparison.json

Six independently authored synthetic cases: clean, unit-price inflation,
legitimate discount, unauthorized fee, authorized fee, and a quantity
overstatement where the billed total was within a pre-stated aggregate
G5 ceiling. The same test input, claim total and source versions were used;
both engines were invoked, and no database rows were changed.

| Metric | A1 deterministic | G5 aggregate deduction proxy |
|---|---:|---:|
| True positives | 3 | 2 |
| False positives | 0 | 0 |
| False negatives | 0 | 1 |
| True negatives | 3 | 3 |
| Precision | 1.0 | 1.0 |
| Recall | 1.0 | 0.6667 |
| Mean measured runtime (ms) | 0.1851 | 0.0527 |

Evidence: https://github.com/overurdream-collab/test2/actions/runs/39053124523
(43 automated targeted tests passed, artifact a1-g5-comparison.json).
The FN belongs to the legitimate aggregate-ceiling issue: the line
quantity disagreed with the attested record even though the approved
test ceiling did not require a G5 tariff deduction.

**Critical caveat:** a nonzero monetary deduction is only a synthetic
*comparison proxy*, not a real G5 review decision. This directly tests the
existing G5 calculation engine, NOT policy-grant authorization, eligibility,
Palermo review, or any medical judgment. Neither percentage may be extended
to arbitrary real claims, codes, contract unit semantics, currencies or
medical records. The current G5 system is left completely unchanged.

All reported claims are independent synthetic fixtures. Audit engine
versions, model weights, source paths, GitHub CI logs and case-by-case
labels are linked above. Failures were preserved rather than omitted.
