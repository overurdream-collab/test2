# DG-001 — L2-SEC-001 Limited Integration Worklog and HANDOFF
Date: 2026-10-19. Status: ISOLATED INTEGRATION / BLOCKED final acceptance.
Branch: integration/mcias-l2-shared-audit. Baseline main b69defa2f621458ef44d790b510840307a81009a.
Source PR25 a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1; source PR27 daf78b6e93fa5e21bb41e4800ce3a7a9ed51c498.
No source branches modified. No production database, merge to main, or deploy.

## Exact provenance and file map
- PR25 unchanged original mcias/audit_writer.py; Git blob SHA 509ce4124f012cc4a121294fe9122c9384902fd6. No PR25 contracts, UI, migration, policy or new router files imported.
- PR27 verbatim mcias/denial_events.py, auth.py, tenant.py, tests/test_tenant_isolation.py, tests/test_l2_denial_transaction_regression.py, tests/test_l2_audit_real_http_pg.py, tests/test_l2_request_owner_contract.py, scripts/l2_sec001_seed.py.
- mcias/app.py: from main, ONE surgical get_db generator replacement matching PR27 handler; preserves all original main API routes and middleware. No PR25 application route additions.
- PR27 mandatory PostgreSQL workflow transplanted; real-writer HTTP and Enterprise integration workflows adapted for clean git checkout: writer MUST be tracked, pinned to the real source blob and importable, with no git fetch, git show or dynamically overlaying writer during CI.
- Integration-only tests/test_l2_audit_failure_propagation.py: failing audit persistence raises, while business changes remain rolled back.

## Final transaction contract
- Guards: raise AuthorizationDenied with server-owned metadata; never commit or rollback.
- FastAPI get_db (request transaction owner): rollback business transaction, invoke denial writer once, propagate any audit writer failure (do not silently convert 500 to 403).
- Shared audit writer: separate Session(bind), reload active matching-tenant actor, bounded allowlisted details, commit one denial after business rollback. Existing PostgreSQL HTTP test confirms one event per attempt, two distinct attempts yield two events, and tenant mismatch writes none.
- Deduplication between endpoint-level 403 and generic owner must be independently reviewed if PR25 contract routes are introduced. They are deliberately NOT included in this isolated limited composition; HTTP retry correlation isn't guaranteed by current writer and requires central contract approval.
- Anonymous actor failures lack trusted actor identity and require separate policy.
- Contract 409 business conflict is outside this branch and remains separately owned.

## Historical fixed evidence (not retested without cause)
- Original both guards RED on PostgreSQL: https://github.com/overurdream-collab/test2/actions/runs/39257009551
- PR27 no-business-commit GREEN: https://github.com/overurdream-collab/test2/actions/runs/39257480016
- PR27 disposable real-writer HTTP GREEN: https://github.com/overurdream-collab/test2/actions/runs/39305148030
- PR27 uncomposed Enterprise FAIL missing writer: https://github.com/overurdream-collab/test2/actions/runs/39305148046
- PR27 temporary real-writer Enterprise GREEN: https://github.com/overurdream-collab/test2/actions/runs/39305147985

## Acceptance gates on this integration SHA
Required: L2 mandatory PG16, L2 real writer HTTP PG16, Enterprise original, Enterprise integrated, G1–G7, G8, G9, relevant Contracts acceptance and no missing imports in clean checkout. CI results must be separately verified, not inferred.
Contracts from PR25 not imported deliberately; no claim of PR25 G3 acceptance running on this stripped branch.
STOP / escalation if tests reveal need for PR25 contract implementation, migrations, or changed RBAC.

## HANDOFF / RESUME
- Read latest integration HEAD and full CI statuses. Verify source module hash and clean checkout.
- Validate no phantom PASS on tests with skipped PG. Read actual denial traceback and AuditLog query assertions.
- Any failing CI: document exact failing job, root cause and minimal scoped remediation, preserve historical evidence; no silent test weakening.
- Remaining blocker: shared writer operational availability via an approved long-lived integration/deployment strategy, idempotency semantics across retries and PR25 endpoint-level denial ownership. Separate central security acceptance required before L2 closes.
- Rollback: do not merge branch, preserve SHA/artifacts, delete only isolated integration branch after review; PR25, PR27 and main remain untouched.
