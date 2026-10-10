# Enterprise workspace installation and deployment

## Baseline and prerequisites

This feature is stacked on `feat/g8-intelligence`, not the README-only `main`.
Use the feature branch or a reviewed integration containing its G1–G8 baseline.
Python 3.11+, PostgreSQL 16, and the existing on-premises security/key configuration
are required for authorized data. Keep a separate database/document store per
organization. Do not deploy production medical records before institutional
acceptance in `ACCEPTANCE_CONTRACT.md`.

```bash
git clone https://github.com/overurdream-collab/test2.git
cd test2
git checkout main
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
cp .env.example .env
```

Configure `MCIAS_DATABASE_URL` and `MCIAS_BOOTSTRAP_TOKEN` in the protected local
configuration, plus existing storage/MFA/signing settings required by the enabled
backend operations. Use the repository’s G1 deployment, MFA bootstrap and recovery
documentation; this UI does not provision accounts or grant roles.

```bash
alembic upgrade head
uvicorn mcias.app:app --host 127.0.0.1 --port 8000
```

Open `/institution/dashboard` and `/admin/dashboard`. Without an authenticated
session, both serve a sign-in state. Super Admin login requires an enrolled TOTP
factor. `/admin/security` supports the existing enrollment/confirmation APIs.
A refreshed browser must sign in again because bearer tokens are memory-only.
Forgot-password uses institution-admin guidance because no recovery API exists.

## Explicit synthetic preview (development only)

Preview requires **both** `MCIAS_ENVIRONMENT=development` and
`MCIAS_ENABLE_UI_DEMO=true`. Default is disabled; production ignores the flag.
No login, real medical data or database connectivity is needed to view synthetic
fixtures, but the existing required settings must be present so environment
validation succeeds. The sample URL below is a nonworking placeholder database,
used only for a visual preview:

```bash
MCIAS_ENVIRONMENT=development \
MCIAS_ENABLE_UI_DEMO=true \
MCIAS_DATABASE_URL=postgresql+psycopg://preview:preview@127.0.0.1/preview \
MCIAS_BOOTSTRAP_TOKEN=synthetic_preview_only \
uvicorn mcias.app:app --host 127.0.0.1 --port 8000
```

Open `/institution/dashboard?demo=1` or `/admin/dashboard?demo=1`. Every screen
carries a synthetic banner and every consequential form is disabled. Fixtures
are deliberately synthetic and never transmitted as backend operations.
No preview amount, comparison or status is inserted into live mode.

## Authorization configuration

Existing backend permissions retain their meanings. The context endpoint needs
`profile.read`; record catalogs reuse `claims.read`, `ingestion.read` and
`reference.read`. The new tenant-scoped user list/detail additionally needs
`users.read` and the `super_admin` role; there are no automatic grants.
Provision permissions through the institution’s approved existing RBAC process,
not by bypassing the database or through unsupported UI actions.

UI restrictions supplement, not replace, backend authorization. The current
institution selector is intentionally disabled: cross-installation tenant
switching and organization administration have no supported API. See the
[route matrix](FRONTEND_ROUTE_API_MATRIX.md) for action-specific rights and gaps.

## Tests and browser verification

No Node dependency is required to run the application. Node 22+ and the single
`axe-core` development dependency are used only by frontend checks:

```bash
python -m pip install -e '.[test,browser]'
npm ci --ignore-scripts
npm test
npm run check
python -m pytest -q
python -m playwright install chromium
python scripts/check_workspace_browser.py
```

Start the development application with preview enabled before the browser suite.
Use `--chromium /usr/bin/chromium` when using an existing Chromium installation.
Output is stored under `.e2e-output/`; the checks assert all 59 workspace routes,
RTL/LTR, themes, responsive layouts, guarded reads, session clearing and WCAG
rules. These tests use labeled fixtures and controlled HTTP contracts.

For the full PostgreSQL suite, use an **empty disposable test database** and
matching `pg_dump`/`pg_restore` clients on PATH:

```bash
MCIAS_TEST_DATABASE_URL='<isolated PostgreSQL test URL>' python -m pytest -q
```

Some inherited test fixtures retain fixed storage keys, so rerunning the entire
suite against an already-used database causes fixture collisions. Use a fresh
disposable database; do not reset an institutional database for testing.

For actual Chromium → FastAPI → PostgreSQL verification, create a **dedicated
empty database ending in `_e2e`**. The seed script refuses other database names
and only creates synthetic data; all seeded claims are held, without fabricated
financial approval:

```bash
MCIAS_E2E_DATABASE_URL='<dedicated *_e2e URL>' python scripts/seed_workspace_e2e.py
MCIAS_DATABASE_URL='<same *_e2e URL>' MCIAS_BOOTSTRAP_TOKEN=synthetic_test_only \
uvicorn mcias.app:app --host 127.0.0.1 --port 8001
python scripts/check_workspace_live.py --base-url http://127.0.0.1:8001
```

The CI workflow `workspace.yml` reproduces browser/contract tests, live PostgreSQL
sign-in/read/logout, accessibility and wheel checks and uploads result files and
screenshots. Existing workflows retain all prior gate regression.

## On-premises deployment

Build with `python -m pip wheel . --no-deps -w dist`. HTML, CSS, ES modules, route
registry, SVG assets, fonts and licenses ship inside the Python wheel. Existing
migrations still run from the source deployment checkout. Serve frontend and
API from the same HTTPS origin behind the institution’s reverse proxy. Do not
introduce a public CDN or send medical requests to a cloud analytics service.

Preserve application CSP, `no-store`, no-referrer and frame-denial headers. The
UI requires only same-origin scripts/styles/fonts/images/connections; inline
scripts and arbitrary filesystem asset paths are blocked. Downloads use the
existing authorized reporting APIs. No signing or storage-encryption key belongs
in browser configuration.

Light/dark and language choices are page-local preferences; no patient or session
state is persisted in browser storage. Production backup, retention, hardware
capacity/SLA, signing authority and accessibility acceptance require the existing
institutional procedures. This feature adds no production financial engine,
policy bypass, tenant switch or immutable-snapshot edit operation.
