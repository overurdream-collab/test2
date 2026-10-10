# External test plan

Document ID: `MCIAS-EXT-001` · Version: 1.0 · Status: Draft for review · Language: English

[النسخة العربية](EXTERNAL_TEST_PLAN.md) · [Package index](ACCEPTANCE_PACK_INDEX_EN.md)

## Starting point and scope

External status: **NOT_EXECUTED**. CI success is not inherited acceptance. The test lead records institution, SHA, image/dependency identities, host, certificates, date and database owners. Start synthetic; any real-data pilot needs separate privacy/policy authority and local transfer. Use the [report template](EXTERNAL_TEST_REPORT_TEMPLATE_EN.md).

## Entry and stop conditions

- Approved scope/hosts/networks, backup/restore and rollback procedures, operators and independent reviewer.
- Complete pinned source/trusted hashes, venv/test dependencies, Node/Chromium, PG16 clients on PATH and separate fresh databases.
- Never run restore/seed/reset/regression on existing institutional DBs. Synthetic regression needs an administrative identity to create temporary roles/restore DBs; it differs from restricted application runtime.
- Stop on unauthorized data, leaked keys, altered originals/snapshots, corruption or out-of-scope outages; retain sanitized evidence and notify authority without further exploitation.

## Execution phases

| ID | Phase | Execution/evidence | Acceptance |
|---|---|---|---|
| EXT-01 | Source/package | Independent SHA, SHA256SUMS, installed dependencies | Match; no secrets/data in package |
| EXT-02 | Target | deploy_check test with restricted runtime, then isolated production-profile | Executed engineering controls pass; not production approval |
| EXT-03 | Regression | Python+PG+restore+Node | No failures; explain every skip/warning |
| EXT-04 | Seed | Two runs in separate Seed DB, compare receipts | No duplication; wrong DB/environment rejected |
| EXT-05 | Browser | Four scripts below and screenshots | RTL/LTR, mobile/tablet and workflows; no errors |
| EXT-06 | Authorization/finance | T06/T07/T08/T11/T15/T20, independent review | Server denial, preserved originals/snapshots |
| EXT-07 | Performance | EXPLAIN, concurrency plan, synthetic P95 | Against signed SLA; otherwise NOT_APPROVED |
| EXT-08 | Archival | Nonempty synthetic institution month, foreign and null actors | Encryption/readback/isolation/no deletion; record exclusions |
| EXT-09 | Recovery | DB+encrypted sources, separate keys/new target | Verified hashes/records, measured RPO/RTO |
| EXT-10 | UAT/security | Paired plans and defect outcomes | Independent signoff after closure; no automatic ACCEPTED |

## PostgreSQL regression

```bash
# Protected session already holds separate synthetic administrative URLs.
export MCIAS_TEST_DATABASE_URL="$MCIAS_REGRESSION_DATABASE_URL"
python -m pytest -q
npm test
npm run check
python -m compileall -q mcias tests scripts
# A different freshly migrated *_e2e DB for the dedicated Seed test:
export MCIAS_E2E_DATABASE_URL="$MCIAS_SEED_DATABASE_URL"
export MCIAS_ENVIRONMENT=development
python -m mcias.seed --output .e2e-output/seed-check.json
export MCIAS_SEED_TEST_DATABASE_URL="$MCIAS_SEED_DATABASE_URL"
python -m pytest tests/seed -q
```

MCIAS_REGRESSION_DATABASE_URL/MCIAS_SEED_DATABASE_URL are operator-session aliases, not application Settings; map them to recognized variables as shown. Use a separate Seed DB. Inherited fixed-key fixtures require fresh regression databases. T17 creates/drops a synthetic restore DB: an intentional authorized test mutation, unlike read-only deploy_check. If the general suite skips Seed, execute it independently and record it; never silently skip PostgreSQL/restore because a suite looks green.

## Browser lifecycle

Provision private MCIAS_STORAGE_DIR and synthetic MCIAS_STORAGE_KEY/MCIAS_MFA_ENCRYPTION_KEY before starting; never print values or use CI values in production.

```bash
# Fresh browser *_e2e database; protected environment supplied by operator.
export MCIAS_ENVIRONMENT=development
export MCIAS_ENABLE_UI_DEMO=true
export MCIAS_DATABASE_URL="$MCIAS_E2E_DATABASE_URL"
python scripts/seed_workspace_e2e.py
python -m uvicorn mcias.app:app --host 127.0.0.1 --port 8000 --no-access-log
# Second terminal inherits the SAME database, storage directory and keys:
python scripts/check_workspace_browser.py --base-url http://127.0.0.1:8000
python scripts/check_workspace_live.py --base-url http://127.0.0.1:8000
python scripts/check_integrated_workflow.py --base-url http://127.0.0.1:8000
python scripts/check_retention_browser.py --base-url http://127.0.0.1:8000
```

integrated_workflow creates a G5 Python/Palermo-2 snapshot fixture; it is **not** production execution API evidence. Generic Seed is metadata-only with no actual original files; upload lifecycle provides original preservation evidence. live-fixture.json/seed-check.json contain synthetic credentials and cannot enter public reports.

## Performance/recovery limits

In another `_e2e` performance DB, run `python -m mcias.seed --count 10000 --output .e2e-output/perf.json`, then `python scripts/benchmark_operational_indexes.py`. Current head already has three indexes, so before may use them too; a meaningful before/after comparison needs a separate performance DB pinned at 0017, never dropping runtime indexes. Empty audit/report tables do not prove composite-index benefit. `python -m mcias.performance_g9 --claims 1000 --repeats 3` is a synthetic computation probe, not API SLA. Agree workload/concurrency/duration and latency/CPU/IO/storage metrics before testing; network flooding is not automatically authorized.

Follow G9_DISASTER_RECOVERY_AR.md for recovery, comparing record/table counts and source/snapshot hashes, not merely health. Bounded archives exclude null actors; legal-hold enforcement, purge and large streaming archives remain blocked future work, never PASS.

## Closure and evidence

For every EXT record SHA, sanitized command, UTC time, environment/data class, metrics, outcome, evidence and defect. Keep originals internally, exclude medical bodies/secrets from reports, and never sum repeated workflow counts. Authorized humans sign each gate under the acceptance contract. Unexecuted/unavailable checks remain NOT_EXECUTED/BLOCKED, not PASS.
