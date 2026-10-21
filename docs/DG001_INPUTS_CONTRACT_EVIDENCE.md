# INPUTS-FIRST — Contract value evidence, independent quality

Baseline: PR23 `e0dd1d162d8e4b6688bec8fef6768c6fbf97051b`. Owner: Contract Intelligence. Latest user authorization permits minimal evidence improvement, synthetic verification only.

`locate_source_value(view, field_id, value)` extends the existing deterministic C35 source view. It emits schema version, original SHA256, record/field identity, source locator and exact half-open character offsets in unchanged field text. Only a unique whole-token literal is accepted. Repeated price values, a date in another cell, or provider H1 embedded in H10 fail closed. Confidence basis is `UNIQUE_LITERAL_SOURCE_SPAN`; model confidence is unknown (`null`), human review remains required and no financial decision is authorized. This is a candidate evidence interface consumable by G5; it does not attest original encrypted bytes, perform inference, approve a reference or extend E1.

Actual local verification on the changed tree (Python3.12):
- `PYTHONPATH=. /workspace/.venv/bin/python -m pytest -q tests/test_contract_source_view.py tests/test_contract_intelligence.py tests/test_contract_intelligence_api.py`: 46 passed, one upstream Starlette deprecation warning.
- `PYTHONPATH=. /workspace/.venv/bin/python -m pytest -q tests/test_contract_source_view.py tests/test_contract_tariff_segments.py tests/test_contract_independent_synthetic.py`: 12 passed.
- Initial API run in socket-restricted sandbox stalled; terminated. Network-enabled sandbox rerun produced the 46-pass result above. No application workaround.

Independent quality on pinned unchanged owner trees:
- A1 PR20 `6af41a04cf887d389656c9ce7ffc4e03b396b5a4`: `tests/test_a1_invoice_integrity.py`, 50 passed.
- Document Reader `d62e2bf` (full hash in Git): scorer + DG002B + human-review scripts, 15 passed. Existing OCR/model qualification limitations remain; no model weights downloaded or model inference run.

First blocker: complete source-authority and independently approved G3 reference integration remains with G2/G3/G5. Actual-model quality is not inferred from these deterministic tests. CI on the published commit is tracked independently; local reports are not CI acceptance. No merge/deploy/real patient data.

Security adoption: include independently verified maintenance8eef408/4892639 (DraftPR33, latest6454b6d all triggered CI PASS). Same review-source behavior; actual audit65external0known vulnerabilities and34compatibility tests previously run. New-head contract CI required.
