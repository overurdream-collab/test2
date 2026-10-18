# DG-001 — G8/G9 migration head compatibility after additive G3 metadata

Previous exact-SHA CI:
- Contracts acceptance PASS: https://github.com/overurdream-collab/test2/actions/runs/39135479309
- G1–G7 checks PASS: https://github.com/overurdream-collab/test2/actions/runs/39135479337
- Enterprise/browser suite FAIL: https://github.com/overurdream-collab/test2/actions/runs/39135479375, due solely to stale G8 PostgreSQL test migration-head equality and G9 preflight hardcoded expected migration revision 0019_input_clauses.
Correct the G8 expected revision to new existing migration head 0020_manual_contract_metadata and G9 least-privilege preflight expected revision likewise. Do not weaken status checks; the preflight still requires exact match. All other controls unchanged.
Acceptance evidence is only provided by a successful new exact-SHA run. Draft PR, no production merge/deploy.
