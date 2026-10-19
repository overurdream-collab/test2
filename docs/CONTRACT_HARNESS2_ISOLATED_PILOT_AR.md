# MCIAS Contract Intelligence — Harness² isolated pilot (research-only)

Status: EXPERIMENT PLAN / NOT INTEGRATED / NO PRODUCTION APPROVAL
Parent baseline: PR #23 `feat/mcias-contract-intelligence` at `39a4a9b93e9eb04ea7c09c8c155c3e08f38c6ec0`
Upstream: https://github.com/google-research/harness2 (Apache-2.0; pin a reviewed commit before use)

## Goal
Test whether iterative harness improvement can improve extraction of exact source-anchored medical-contract clauses and tariff amounts without changing weights, financial rules, database schema, existing PR #23, or independent human-review requirements.

## Security boundary (mandatory)
- Only fabricated contracts and synthetic benchmarks. No PHI, customer information, Gmail, operational database access, secrets, or production URLs.
- Run in a dedicated isolated executor with outbound networking disabled by default; any model endpoint must be explicitly approved and constrained to synthetic data.
- No Docker socket mount, privileged containers, host volume mounts, implicit CLI credentials, or access to GitHub write tokens.
- The harness optimizer may propose versions of prompts, tool guidance and transient memory only. Guardrails, audit, authentication, approval workflow, trusted reference sources, SQL, and financial logic remain immutable.
- Candidate edits cannot execute commands, edit repository files, edit guardrails, write database state, or push commits. A separate trusted evaluator executes a strict allowlist.
- Reject any proposal seeking network access, tool privilege escalation, hidden evaluation answers, benchmark-specific hardcoding, relaxed source anchoring, or a bypass of HUMAN_REVIEW.
- Fail closed on absent isolation proof, unavailable prerequisites, missing benchmark results, or unexpected exceptions.

## Baseline, evidence and evaluation
1. Capture exact SHA for Contract Intelligence and upstream Harness²; snapshot benchmark versions and frozen test cases.
2. Read existing synthetic Contract AI benchmark and C33 isolated-tariff test definitions and obtain reproducible baseline; do not label a CI run as a successful model-quality benchmark merely because its workflow passed.
3. Split synthetic cases into optimization and hidden holdout; never reveal holdout labels to the editing agent.
4. Measure baseline and candidate on identical pinned model, decoding policy, seeds where supported, source documents, and evaluation harness.
5. Log counts TP/FP/FN, precision, recall, clause-source anchoring, exact amount/currency, service date, provider segmentation, quarantined hallucinations, runtime and token cost.
6. Include adversarial and regression suites, especially cross-provider tariff contamination and prompt injection inside source PDFs.
7. Accept only after no security regression, no rise in false positives, improved holdout recall and amounts, and independent reviewer authorization. Otherwise revert candidate.
8. Preserve evidence in isolated artifacts with SHA, invocation parameters and redacted logs.

## Phases
- P0: baseline inventory and threat review (read-only).
- P1: deterministic offline smoke test of upstream local demo, only inside strict container.
- P2: minimal prompt/tool-guidance candidate generator against synthetic cases.
- P3: holdout and negative security evaluation.
- P4: evidence report and explicit owner decision. No merge or deployment by automation.

## Stop conditions
Any access to operational assets, no reproducible baseline, a candidate modifying guarded components, hidden-test contamination, unexpected network egress or any security/financial control regression stops the pilot immediately.

## Current evidence
On 2026-10-19: confirmed PR #23 is draft at `39a4a9b93e9eb04ea7c09c8c155c3e08f38c6ec0`; main at `b69defa2f621458ef44d790b510840307a81009a`; upstream README documents a credential-free deterministic demo via `harness2-demo`. No model-backed pilot, isolated sandbox, or benchmark execution is claimed by this document.
