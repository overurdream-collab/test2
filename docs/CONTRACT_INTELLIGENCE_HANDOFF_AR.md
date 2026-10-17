# Contract Intelligence — استلام فوري للمبرمج وCodex

**مشروع:** overurdream-collab/test2 / branch feat/mcias-contract-intelligence / base PR #22 (unmerged). **R0 status:** research and architectural specification documented; no model inference demonstrated. Read CURRENT_STATE and EXECUTION_JOURNAL first; never interpret docs as deployed behavior.
## Do first
1. Fetch latest branch HEAD from GitHub, compare with parent feat/temporal-reference-inputs-and-four-outcomes and review linked Draft PR.
2. Read docs/CONTRACT_INTELLIGENCE_OPEN_SOURCE_RESEARCH_AR.md, ARCHITECTURE, TEST_REPORT, DECISION_REGISTER; code: ingestion/reader_agent.py, orchestrator.py, reference_points.py, reference_rule_bridge.py, app.py, models_ingestion.py and 0019.
3. Run python -m pip install -e '.[test]' then python -m pytest -q tests/test_g2_ingestion.py tests/test_reference_rule_bridge.py tests/test_reference_points_and_outcomes.py tests/test_reference_points_http_security.py; use isolated MCIAS_TEST_DATABASE_URL for PG and Actions for comprehensive checks.
4. **Next task:** add synthetic generation and JSON schema evidence validator in a small commit with HANDOFF and CURRENT_STATE; then model inference adapter behind disabled-by-default flag; do not persist AI output as ReferencePoint automatically.
5. Real model is NOT_RUN. No model version/weights/hash, benchmark, accuracy metric or GPU availability has been established. Have on-prem isolated runtime approved before using any live institution input.
## Invariants
Never merge or deploy, pay for models, expose PHI, change main, update approved financial history, call G5 directly from LLM, create A1, approve points without institutional bound signature. Each commit must contain 8 HANDOFF fields + CURRENT_STATE and developer/acceptance updates if applicable; CI on exact SHA, PENDING_CI otherwise. Handoff must state precise remaining work.

## C1 first code commit
Review mcias/contract_intelligence.py and tests/test_contract_intelligence.py; check actual GitHub Actions. The model endpoint is deliberately only 127.0.0.1/localhost with /v1/chat/completions; no runtime configured so real Qwen inference is NOT_RUN. Next must connect G2 record/job tenant-scoped API and preserve field-level permissions, then begin true model benchmarking. No ReferencePoint inserted automatically.

## C2 next steps
Preview API lives in mcias/contract_intelligence_api.py, route app.py, browser reference_points_view.js. Requires G2 document status extracted, trusted locator fields, existing RBAC and explicit local model vars. No persistence or automatic approval; C2 tests mock model. Check exact SHA CI, fix failures, run isolated on-prem model with SHA/weights revision then build persisted candidate review workflow as new additive migration, updating expected G9 migration head as appropriate.

### C3 targeted regression
Fixes failing G1-G7 unit on 1d84f576: provider_code list caused TypeError. Newly added two-prices-same-page test. Look up CI for C3 exact SHA and record evidence before any further work. C1 local-only LLM runtime still NOT RUN.

### Resume C4
- Run python -m pytest -q tests/test_contract_documents.py alongside tests/test_contract_intelligence.py and tests/test_contract_intelligence_api.py. Exact CI required; if PDF parser test fails inspect source MIME/file_scanner limits before altering G2. No institutional data, no new parser. Next typed rules and real local model inference.

### C5 resume
Read mcias/contract_rule_compiler.py + tests/test_contract_rule_compiler.py and check HEAD CI. Diagnostic compiler never executes financial policy. Next a local model real inference with weight/model revision and replayable samples, then persistent proposals and independent human review; no activation.

### C6 resume: source-anchored persisted proposals
- New models_contract_proposals.py and migration 0020 implement tenant-bound immutable proposal/review/promotion history. contract_proposals_api.py defines /extract, /documents/{id}/proposals, /proposals/{id}/review and /promote. No raw AI result supplied by client is accepted. Source G2 fields are checked for permissions again on review. Only independently reviewed complete candidates promote to an INACTIVE ReferencePoint draft, not to finance execution.
- Tests: tests/test_contract_intelligence_api.py; PostgreSQL and full CI on new SHA PENDING. Real Qwen inference, Arabic OCR benchmark, UI reviewer journey, institutional signatures all NOT_DONE. Never merge or deploy.


### C7 CI fix resume
C6 SHA 88ec7edb had FAIL on tests due mock-auth fixture and migration head; see Test Report. C7 supplies fixture and 0020 head updates (test-only and G9 preflight). Run exact-head G1–G7, G9, Enterprise and DG Actions. Real local Qwen, UI review and signed approval are still open and must not be represented as complete. Never merge or enable financial authority.


### C8 handoff — real pretrained proof and human UI
The `reference_points_view.js` drawer now supports persisted /extract and a separate review/propose UI for users having `reference.read` + `ingestion.read`, and `reference.approve` for human review. Branch C8 adds `scripts/contract_ai_benchmark.py` and `.github/workflows/contract-ai-benchmark.yml` for local loopback Qwen3-0.6B model, pinned SHA, 4 synthetic cases and measured evidence. Inspect exact Actions before saying any model run passed. Hosted public standard GitHub runners are free; no external sensitive records or financial activation. If the synthetic benchmark fails, record model loading or malformed-JSON error and continue only with evidence. Expand Arabic/scanned/Excel gold corpus before complete acceptance. Do not merge or start A1.


### C9 actual pretrained model blocker
C8 real Qwen3-0.6B generated 4 outputs but zero source-verified clauses: TP0 FP0 FN3, Recall0, Precision undefined (Action run 39063356685). Diagnose as model JSON schema mismatch, not a working functional agent. C9 script adds safe previews of *synthetic-only* outputs and fails the quality job when zero useful clauses. Fetch new benchmark logs/artifact; update reporting with raw evidence. Never send real insurance files to a public runner. Remaining: prompt/schema correction, repeatable real inference, larger 20+ contracts, Arabic OCR, review UAT, signatures, no main merge or A1.


### C10 — JSON-constrained pretrained experiment + raw SQL guard
C9 SHA daa4b934f84fd2e7bfefa0ed4de298b8c5178f0a: all ordinary governance/G1–G9/Enterprise workflows success, but real Qwen3-0.6B benchmark FAILED https://github.com/overurdream-collab/test2/actions/runs/39063739175 (TP0 FP0 FN3, malformed fenced arrays and wrong schema). No acceptance. C10 adds lm-format-enforcer v0.11.2 **benchmark-only** constrained JSON output, generic few-shot prompt, and tests/test_contract_proposal_postgres.py to prove proposed/review/promoted immutable tables resist direct SQL changes. Test on exact C10 SHA pending; review CI, see model generated hashes/source anchors, fix only without bypassing validator. Real patient/private files forbidden, no production approvals, deployment, PR merge or A1.
