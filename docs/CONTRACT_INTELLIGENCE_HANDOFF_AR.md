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
