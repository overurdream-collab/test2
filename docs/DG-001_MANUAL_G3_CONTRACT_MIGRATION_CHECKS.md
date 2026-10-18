# DG-001 — Existing PostgreSQL migration-head assertion update

Previous acceptance commit: d65f307240b1b95154ba8f3ac38853d9f15ee1fd
- Contracts strict Chromium/PostgreSQL PASS: https://github.com/overurdream-collab/test2/actions/runs/39135272209; import PASS, manual Add PASS, reader RBAC PASS, Edit BLOCKED.
- General postgres-integration FAIL: https://github.com/overurdream-collab/test2/actions/runs/39135272239. Five older tests asserted Alembic head == 0019_input_clauses; additive migration 0020_manual_contract_metadata deliberately advances Alembic head. These are stale HEAD identity assertions, not migration failures.
- Update exactly five asserted expected revision values to 0020_manual_contract_metadata, keeping all test bodies, G3/G5 financial guards, and production behavior unchanged. Re-run exact SHA before acceptance. No main merge or deploy.
