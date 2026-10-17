# A1 — InvoiceIntegrity Agent (experimental standalone)

**Status:** IN_PROGRESS / synthetic evaluation only. **Not production-accepted.**
Scope: A1 ONLY. PR #19 is an unmerged, advisory architecture draft, not a main dependency.
Baseline inspected: main @ b69defa2f621458ef44d790b510840307a81009a.

## Inventory: preserve, do not rebuild

- G2: mcias/ingestion/reader_agent.py, isolated PDF/CSV/XLSX/OCR ingestion and Palermo-1.
- G3: mcias/models_reference.py, mcias/reference.py, mcias/tariff_import.py:
  approved, effective-date provider contracts and currency-specific service tariffs.
- G4: mcias/models_claims.py: immutable tenant-scoped claim sources and attachments;
  the present claim is a *single* service_code + aggregate claimed_amount, not a
  trustworthy structured itemized invoice.
- G5: mcias/audit_agents.py: eligibility, contract, tariff, exclusion, caps,
  cost_sharing, duplicates, evidence; mcias/audit_engine.py: Decimal financial
  policy; mcias/palermo2.py: independent reconciliation.
- G6/G7/G8: human governance, reporting and intelligence are pre-existing.
- There is no verified real LLM in the existing deterministic G5 path.
  Do not treat a G5 tariff existence check as a line-item overcharge comparison.

## Experimental A1 contract

Entry point: mcias.agents.invoice_integrity.analyze(bundle, model=None, model_id=None)
Return: read-only JSON with tenant_id, run_id, claim_id, agent_id/version, ruleset
version, model id/version/status, PASS/REVIEW/INSUFFICIENT_EVIDENCE/HELD,
itemized finding_type, evidence_refs (document_id/SHA-256/locator),
missing_evidence, financial currency, policy_version, fingerprints, and a
human-review-only flag. Financial amounts are suspected indicators, NOT
approved deductions or realized savings. No writeback, automatic approval,
rejection, fraud claim, accounting mutation, or production API.

Input bundle is an **immutable, authenticated, tenant-scoped snapshot supplied
by an upstream trusted adapter**. The standalone module does not query databases.
Claim/invoice/service records and approved contracts each require scoped
provenance; invoice items require explicit code, quantity, unit, unit price,
line amount, source, and kind. Currency is never converted or guessed.
A unique approved effective-date contract is required, with half-open dates
[effective_from,effective_until); overlaps hold/abstain.

Existing G3 ProviderTariff rows do not include per-service quantity units; a
future trusted adapter must establish the authorized unit basis. **Never infer
per-unit meaning from existing tariff.amount.** A1 input uses explicit unit
and unit_price and is not a direct production mapping from the G3 database.
No approved data rows are changed.

Deterministic rules: compare each line with explicitly unit-matched, currency-
matched active contract tariff; reconcile Decimal unit * quantity, item totals,
invoice total and claim total. Quantity anomaly only when exactly one attested
matching service record exists (do not treat unverified OCR as attestation).
Undocumented fees only generate REVIEW when approved contract explicitly
declares the fee schedule exhaustive. Missing/ambiguous evidence yields
INSUFFICIENT_EVIDENCE, not an overcharge assertion.

LLM: separate callable interface; candidate text contradictions are validated
against an exact quote in an explicitly cited local synthetic source.
Its advice may create a REVIEW signal; cannot set a monetary adjustment.
A missing/failed model is observable as NOT_CONFIGURED or MODEL_OUTPUT_INVALID.
Experimental LLM invocation explicitly refuses non-synthetic bundles.
A quoted snippet does not prove the model's interpretation is correct: an
independent reviewer must assess semantic truth and source authenticity.
Document SHA-256 metadata is supplied by the caller, *not recomputed against
external source files by this prototype*. This is a planned Palermo verification.

## Real open-weight model experiment

Suggested target for future evaluation: Qwen3-8B (Apache-2.0), via local
llama.cpp with verified model weights. On limited free CI CPU we probe
**Qwen3-0.6B GGUF only**, expressly a feasibility smoke, not an 8B-equivalent
accuracy benchmark or a medical system qualification.

To run the REAL weight-inference experiment without paid APIs:

    python -m pip install "llama-cpp-python>=0.3.9,<1" "huggingface_hub>=0.30,<2"
    python -m scripts.a1_probe_local_model --download-public-model

This downloads **only public model weights** (official Qwen repo); the model
runs in-process using CPU, and fixture contents are never uploaded.
Alternatively supply --model-file /trusted/local/model.gguf to avoid download.
The generated a1-real-model-evidence.json contains SHA-256 of actual weights,
model revision, two raw generated responses, token usage, RSS and latency.
No simulated model output qualifies as real inference. The fake test callback
in tests/test_a1_invoice_integrity.py tests JSON guardrails ONLY and is
explicitly named a stub.

## Reproducible synthetic tests

    python -m pip install -e '.[test]'
    python -m pytest tests/test_a1_invoice_integrity.py -q
    python -m scripts.evaluate_a1 --output a1-results.json

Hand-labeled fixture specifications and gold statuses:
tests/a1/synthetic_cases.py::GOLD; 18 fixed synthetic scenarios. Their
labels were authored independently of model output. Separate tests exercise
line arithmetic, contract date cutoffs, tenant/currency isolation, OCR and
missing quantity, allowed/unsupported fees, document prompt injection,
exact quote checks, and prevention of invented monetary authority.

Precision = TP/(TP+FP); recall = TP/(TP+FN), using REVIEW as positive.
INSUFFICIENT_EVIDENCE cases are counted as abstentions separately, not
relabelled as true negatives. This tiny, contrived dataset cannot establish
real clinical accuracy; measure additional blind expert-labeled cases.
Latency/RSS in synthetic rules-only mode excludes PDF ingestion, OCR,
network, database, model startup and model tokens. "100% synthetic rules
precision" is NEVER "100% AI precision." Model quality needs distinct blind
labels and independently reviewed clinical/contract evidence.

Current G5 comparison: the existing policy engine computes approved
aggregate-claim tariffs and reconciles deductions. It is not a directly
comparable classifier on A1's multi-line invoices. Any numeric accuracy
comparison without a common approved adapter and labeled corpus is N/A.
Existing code and tests were preserved, not replaced.

## Interfaces for later integration (NOT implemented)

Professor OS -> trusted upstream snapshot -> A1 candidate signals ->
independent Palermo-2 validation -> G6 human review -> G7 reports /
non-overlapping SavingsLedger attribution. Model Gateway may implement
the Callable separately. Reject overlapping or cross-tenant contract/source
retrieval before A1. Bind institutional policy versions and immutable raw
source checksums. A1 does not modify approved contracts or claims.

## Acceptance blockers / outstanding

1. Obtain successful **real** model inference trace; separately qualify
   appropriate model for contract/invoice reasoning on an expert-adjudicated
   blind dataset, including FPs/FNs and tenant/injection robustness.
2. Build the *trusted upstream adapter* from immutable G3/G4 records,
   preserving actual approved quantity-unit semantics and document locations.
3. Palermo independent verification of model citations and raw file hashes.
4. Institution-specific policy authorization, human review, security, and
   deployment gates, explicit manual approval. G0–G9 remain OPEN.
5. Do not merge automatically; finish reviews first.
