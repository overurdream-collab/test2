# DG-001 — G3 manual contract revision acceptance (contracts only)

Base SHA: 5bce6673e8135c33b706f7e3b2bb4fadff887aaa, Draft PR #25. Scope: **Edit** only; the earlier Import and Add paths stay unchanged.

Existing G3 `ContractVersion` uses tenant+provider version sequence, immutable approved records, separate authorization/approval, G3 audit logs, and persisted contract_number, effective dates and notes. Current contract-section Edit was incorrectly wired to InputClause revision and could not select a G3 contract.

This additive change reuses G3: a writer chooses an existing G3 contract in the contracts workspace and opens a prefilled notes/dates/precedence form. The number, organization and provider are immutable in the revision request; the reference service appends a new draft `ContractVersion`, retaining the original row and original tariff rows without modification, with `contract_draft_revised` audit event recording `previous_id`, `previous_version`, actor and timestamp. Existing G3 approval controls remain entirely separate. The provider-wide PostgreSQL advisory transaction lock and latest-version comparison reject stale requests with HTTP 409. Reader without reference.write is forbidden.

Dedicated strict Chromium+FastAPI+PostgreSQL 16 test continues to prove import and manual add; for Edit it selects synthetic G3 contract in the actual page, verifies prepopulated values, edits notes only, submits browser POST, reads both DB versions, checks original untouched, distinct IDs, version sequence, created_by/created_at, audit predecessor and zero tariffs / approval. It explicitly attempts stale writer retry (409), unauthorized reader revision (403), invalid dates (409). Screenshots named 10-selected-existing-g3-contract.png to 13-contract-version-history.png and results.json are uploaded as Actions artifact even on failure. PASS only when exact-SHA CI corroborates.

Limits: the separate business process to approve/activate a contract remains untouched. Editing approved contracts is forbidden. Provider-wide version concurrency is deliberately conservative. No other input sections, paid services, production deployment or main merge.
