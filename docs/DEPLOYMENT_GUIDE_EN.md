# External environment installation and operation

Document ID: `MCIAS-DEP-001` · Version: 1.0 · Status: Draft for review · Language: English

[النسخة العربية](DEPLOYMENT_GUIDE.md) · [Package index](ACCEPTANCE_PACK_INDEX_EN.md)

## Scope and prerequisites

Prepare an **isolated external test environment**, not production authority. main is the engineering source; freeze a full SHA before transfer. Tested requirements: Linux, Python 3.12 (project supports 3.11+), PostgreSQL 16 with compatible pg_dump/pg_restore, Node 22+ and Chromium/Playwright for tests only. The institution approves storage/workload/concurrency/RPO/RTO; no invented capacity targets.

Owners: DBA for migrations/roles, operator for restricted runtime, security for certificates/keys/scanner, independent evidence reviewer. Never deploy `.env.example` passwords or CI keys.

## 1. Freeze and verify the source transfer

```bash
git clone https://github.com/overurdream-collab/test2.git
cd test2
# MCIAS_RELEASE_COMMIT: full independently reviewed SHA, supplied out of band.
git checkout --detach "$MCIAS_RELEASE_COMMIT"
git rev-parse HEAD
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test,browser]'
npm ci --ignore-scripts
python -m playwright install --with-deps chromium
```

For offline transfer, compare `HANDOFF.json`/`SHA256SUMS` against an independently trusted copy, then install the verified wheelhouse into a fresh venv. A checksum is not an acceptance signature. Full source is required for migrations/tests/operator scripts; the wheel alone is insufficient. Never transfer `.env`, `deploy/private`, `.e2e-output`, original medical files or old host keys.

```bash
# Verified candidate/wheels from an institution-controlled handoff.
python -m pip install --no-index --find-links candidate/wheels mcias
python -m pip check
# Full committed source is still required for Alembic, tests and operator scripts.
```

## 2. Separate databases and identities

- Fresh regression DB, separate `_e2e` browser DB and isolated restore DB; never run pytest on institutional data.
- Separate owner/migration and runtime accounts. Runtime owns no tables, has no superuser/CREATEDB/CREATEROLE/REPLICATION/BYPASSRLS, public-schema CREATE or audit_log UPDATE/DELETE.
- DBA reviews actual per-table/action grants. API counters require SELECT/INSERT/UPDATE/DELETE on `api_rate_limit_buckets`; preflight requires SELECT on `alembic_version`. There is no general RLS; API guards and some database consistency checks provide tenant enforcement. End users must not receive direct SQL access.
- Deployment does not create Super Admin or institutional privileges automatically. Use an authorized local identity/MFA procedure. `python -m mcias.bootstrap_mfa --username USERNAME` prints a one-time TOTP secret; run only in a private unrecorded console.

## 3. Local configuration and key custody

Load values through protected institutional secret management/service configuration. The checker neither reads nor executes `.env`. Never put values in reports or use `set -x`/environment dumps.

| Variable | Use |
|---|---|
| `MCIAS_DATABASE_URL` | Intended runtime PostgreSQL+psycopg identity; secret, not a command-line argument |
| `MCIAS_TEST_DATABASE_URL` | Fresh administrative synthetic regression DB; never production |
| `MCIAS_E2E_DATABASE_URL` | Separate browser/Seed DB ending `_e2e` |
| `MCIAS_ENVIRONMENT` | `development` for synthetic tests; `production` for production-profile checks only |
| `MCIAS_RELEASE_COMMIT` | Exact reviewed 40-character SHA |
| `MCIAS_STORAGE_DIR`, `MCIAS_STORAGE_KEY` | Local private encrypted-source directory, 32-byte hex key |
| `MCIAS_MFA_ENCRYPTION_KEY` | Independently held nonzero 32-byte hex key |
| `MCIAS_AUTHORIZATION_REGISTRY` | Protected, locally provisioned institution-head trust registry |
| `MCIAS_G5_POLICY_VERIFICATION_KEY` | Separate local G5 HMAC verification secret; never a browser setting |
| `MCIAS_TLS_CERT_PATH`, `MCIAS_TLS_HOST` | Exact-host SAN certificate used by preflight |
| `MCIAS_MALWARE_SCAN`, `MCIAS_CLAMAV_HOST`, `MCIAS_CLAMAV_PORT` | Production requires `clamav`, loopback scanner, approved port |
| `MCIAS_RETENTION_ARCHIVE_DIR`, `MCIAS_RETENTION_ENCRYPTION_KEY` | Optional local archival worker directory/key; no purge |
| `MCIAS_ENABLE_UI_DEMO` | Explicit development preview only; disabled for production-profile checks |
| `MCIAS_BOOTSTRAP_TOKEN` | Development-only bootstrap; absent in production |

Precreate source storage owned by runtime with mode 0700; use 0600/minimum privilege for private files. deploy_check neither creates a probe file nor changes chmod. Escrow keys separately from data with independent recovery authority; browser configuration contains no keys.

## 4. Migrate and start

```bash
# Administrative migration session, separate from runtime credentials.
alembic upgrade head
alembic current
# Switch to runtime identity/environment before starting the API.
python -m uvicorn mcias.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

Current head is `0018_claim_query_indexes`. Switch to restricted runtime after migration, never run HTTP as DBA. `/admin/dashboard` and `/institution/dashboard` expose sign-in states without records before authentication. External exposure needs an approved institutional HTTPS proxy and explicit trusted proxy addresses, never `*`; the API does not parse caller Forwarded headers itself.

Optional engineering Compose harness: internal PostgreSQL, non-root API and localhost-only TLS `127.0.0.1:8443`. Provision `deploy/private/{runtime.env,postgres-owner.env,authorization-registry.json,tls.crt,tls.key,encrypted-sources/}` outside Git, then `docker compose -f deploy/compose.g9.yml up -d --build` after network/permissions review. Images use mutable tags and builds download dependencies; pin reviewed digests/offline wheels before production release.

Compose does not provision ClamAV. The application accepts loopback scanner hosts only, so place it within API's network namespace/host according to an approved design, not an unsupported separate-container hostname. Production uploads fail closed without scanner; never disable it to bypass failure.

## 5. Interpret target-host checks

```bash
# Run from the reviewed source checkout with an active runtime environment.
umask 077
./scripts/deploy_check.sh --profile test \
  --url http://127.0.0.1:8000 --expected-commit "$MCIAS_RELEASE_COMMIT" \
  > /secure/operator-evidence/deploy-check.json
# For an institution-hosted, configured production-profile test:
./scripts/deploy_check.sh --profile production \
  --url https://mcias.test.institution.example \
  --expected-commit "$MCIAS_RELEASE_COMMIT" --ca-file /secure/institution-ca.crt
```

The .sh wrapper runs deploy_check.py with python3 or selected `MCIAS_CHECK_PYTHON`. GETs cover health, public login and production-disabled public API docs; no login, upload, migrations, Seed, policy changes or medical API probes. PostgreSQL uses only existing preflight SELECTs. Local ClamAV receives PING, never a document. Timeouts are bounded, redirects rejected and TLS verified with no insecure option; origins containing userinfo/query/path are rejected.

Exit `0`: every required engineering control passes, not institutional approval. `2`: BLOCKED, including `--skip-database` or an archive without Git identity requiring separate integrity review. argparse returns 2 for usage errors. JSON excludes full URLs, secrets and HTTP error bodies. Run within the intended runtime context; incorrect permissions fail closed. This does not prove key rotation, registry authority, malware accuracy, backup/restore, firewall or SLA.

## 6. Operations and rollback

Optional `python scripts/retention_worker.py` runs under a local scheduler/restricted account, verifying completed-month archives without audit deletion. `--cleanup-rate-buckets` only clears old operational counters. Archives are not full DB backups and omit null-actor logs; RETENTION_POLICY documents bounds.

Before upgrades: freeze source/hashes, back up DB/encrypted source storage with separate key custody, and test restore in a fresh database. Several append-only migrations cannot downgrade; never treat `alembic downgrade` as a general rollback plan. Authorized rollback restores a consistent snapshot with matching application version. Execute [external tests](EXTERNAL_TEST_PLAN_EN.md), UAT and independent penetration tests; this guide alone does not authorize real data or financial activation.
