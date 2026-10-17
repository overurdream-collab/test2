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


### C11 resume — corrected prompt quotes
C10 new real-model harness could not import `mcias.contract_intelligence` due accidental doubled escapes before embedded JSON quote characters at line 237. CI https://github.com/overurdream-collab/test2/actions/runs/39064329834 and model run 39064329875 FAIL. C11 repairs Python syntax in prompt only, not validator/financial guard. Verify compileall, all CI, constrained pretrained model JSON accuracy and PostgreSQL immutable test after commit; until observed all PENDING. No merge, production, real files or A1.


### C12 next action
- C11 real-model evidence at SHA bee37b2d: JSON correct but every valid synthetic source returned zero clauses; Actions 39064533187 functional FAIL (TP=0, FP=0, FN=3). The new C12 source-only benchmark compares Qwen3-1.7B official revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e without modifying application runtime/finance.
- Inspect Contract AI real-model synthetic benchmark Actions on new SHA, capture actual model load/memory errors if any and full TP/FP/FN/response SHA. All work on Draft PR23 child of unmerged PR22; no PHI/public uploads, paid servers, merge, production, A1 or automatic finance.


### C13 resumption
- Exact C12 1.7B benchmark run 39064879988 was an evidence-backed **FAIL**: 4 empty structured outputs, TP0 FP0 FN3. Avoid classifying 0 FP with no model positives as success.
- New `tests/test_contract_gold_battery.py`: 20 positive synthetic source snippets spanning eight categories and 10 intentionally invalid updates; run `pytest -q tests/test_contract_gold_battery.py` as unit tests. This verifies only quote/type/dates/provider checks, not actual AI extraction or OCR.
- Enterprise run 39064879967 failed a rate-limit check; rerun requested and investigation open. Fetch fresh branch head and checks before proceeding. Remaining: actual validated clauses from pretrained model, large document gold, Arabic OCR and signature-bound institutional UAT. No merge/main/production/A1.


### C14 — diagnostic differentiation
- C13 deterministic 30-case gold-anchoring suite passed as part of G1–G7 (run 39065318369), not AI benchmark. C14 test-only script forces at least one structured proposal in ALL four SYN model prompts (including adversarial negative), while source validator stays strict and false-positive gate is explicit. No production runtime or signed finance changes.
- Retrieve C14 exact GitHub Actions output: how many candidates generated, how many quarantined, TP/FP/FN on verified source anchors, any model/timeouts and artifact hashes. Do NOT use forced-nonempty metrics as normal model-selection accuracy. Next: assess more capable model or two-stage classifier+extractor; expand 20+ real-structure SYN documents and local Arabic OCR.


### C15 date lineage
- Open mcias/contract_intelligence.py `validate_candidates` and tests/test_contract_intelligence.py: for PDF/image, verify date inside quote; for sheet/row, permit date in same persisted G2 record fields. Unknown or inferred effective date must not silently authorize tariff version.
- Run targeted pytest + full CI and inspect C14 forced model experiment before applying any other changes. No actual contract data/public runner use, no main merge, production, signatures, A1 or financial rule activation.


### C16 resumption — example contamination and grounded dates
- C14 real Qwen diagnostic all 4 generated candidates copied P7:XRAY from system-prompt sample and got quarantined (run 39065549717). C15 stricter date proof rightly exposed two bad synthetic fixtures, causing G1–G7/Enterprise failures (run 39065759298). C16 removes prompt sample constants and corrects test *source quote and row* (not validator). Check new full CI and real model errors/TP/FP/FN.
- Review mcias/contract_intelligence.py, tests/test_contract_intelligence.py, tests/test_contract_intelligence_api.py. Do not re-introduce numeric/provider examples into system instruction; do not drop source date validation. No production, main/merge, A1 or model-specific financial authority.


### C17 resume
- Latest C16 unittest regression was SyntaxError at fake local model JSON `choices` list (Actions run 39066030984), not a production code import issue. New C17 fix is test-only. Review exact C17 G1–G7, G8, G9, Enterprise and model bench results after commit; preserve strict source date evidence and no hardcoded system-prompt tariff identities. Continue only Draft PR23, no main merge, deployment or A1.

### C18 next resume — timing test and actual model blocker
C17 real-model run 39066166029 FAIL: four source-unverified proposals, wrong IDs and missing numeric values, Recall0/3; example contamination fixed but pretrained extraction still unusable. All G1–G9 regular tests and governance PASS, Enterprise 39066166119 FAIL one intermittent wall-minute-rollover limit test. C18 test-only fix pins rate-limit now while still executing actual middleware; CI on new SHA PENDING. Inspect current PR23 head, all C18 Actions, then resume rigorous real-model/source tests. Never use private data or bypass signed G3/G5 controls, no merge or A1.
