# G7 — Versioned Reporting (engineering delivery)

Status: **IMPLEMENTED FOR SYNTHETIC ENGINEERING TESTS / OPEN FOR INSTITUTIONAL ACCEPTANCE.** This work is based on G5/G6 engineering code and is not a waiver of G0–G6 acceptance or the pending MCIAS policy pack.

## Components
- `0014_g7_reporting`: PostgreSQL append-only `report_snapshots`, unique `(batch_id,version)`, database trigger checks active same-organization actor and batch. No destructive downgrade.
- `reporting_g7.py`: approved/held derivation from latest G5 audit snapshot and versioned G6 governance decision, strict per-currency Decimal totals, frozen SHA-256, old-version stability and source-column retention. Only completely imported batches are currently eligible; no silent partial import.
- `report_exports_g7.py`: Excel executive summary, permission-gated original-source worksheet, PDF aggregated executive report without patient identifiers. Original Excel strings are marked text to avoid Excel formula injection or numeric-identifier coercion.
- `reporting_g7_api.py`: protected version creation, summary/dashboard JSON, Excel, PDF, beneficiary statement. No source-value API is available to a user without extra `reports.originals.export` permission **and** an individually authorized `medical_fields.<column>.read` permission for every column.
- Source rows and document SHA-256 are copied into frozen snapshots for T18 provenance; no raw claim edit takes place.
- Reports do not assign insurance liability to held, objected, unverified or unreconciled items.

## API (all require bearer authentication; permissions default deny)
| HTTP | Endpoint | Required |
|---|---|---|
| POST | `/api/v1/reports/batches/{batch_id}/snapshots` | `reports.create`, `claims.read` |
| GET | `/api/v1/reports/snapshots/{report_id}` | `reports.read` |
| GET | `/api/v1/reports/snapshots/{report_id}/dashboard` | `reports.read` |
| GET | `/api/v1/reports/snapshots/{report_id}/excel` | `reports.export` |
| GET | `/api/v1/reports/snapshots/{report_id}/excel?include_originals=true` | above + `reports.originals.export` + every column medical-field permission |
| GET | `/api/v1/reports/snapshots/{report_id}/pdf` | `reports.export` |
| POST | `/api/v1/reports/snapshots/{report_id}/beneficiary-statement` | `reports.beneficiary.read`, `medical_fields.beneficiary_token.read` |

Beneficiary statements carry `beneficiary_token` in an authenticated POST JSON body, never in a URL or query string, to reduce proxy-log disclosure.

The dashboard API provides privacy-minimized financial metrics. A responsive Arabic RTL browser dashboard is served at `/ui/reports`, with same-origin script/style, strong CSP, no-store headers, and no persisted browser session tokens. Reports are created explicitly by authorized staff and do not imply payment authorization.

## Tests
Run `python -m pytest -q tests/test_g7_reporting.py tests/test_g7_postgres.py` under the CI PostgreSQL environment, plus full regression.
- **T13:** frozen version 1 does not change when a later G5 result arrives.
- **T18:** original columns, strings such as `0012300`, and literal cells beginning with `=` remain intact.
- **T20:** approved and held totals reconcile independently per currency, and unauthorized sensitive originals are denied.
- Other cases: open objections zero payable; malformed G5 amount held; cross-tenant mixing denied; tampering detected; invalid or partial batches blocked.

## Important outstanding controls
1. An institution must approve financial rules, report format and which fields require elevated access. Default-deny protects against unapproved use.
2. The 10,000-claim in-memory ceiling is a provisional engineering guard, not an approved workload/SLA. Realistic stress tests, streaming and snapshot transaction-isolation assurance are pending.
3. Arabic RTL Excel and Arabic PDF generation are implemented. The PDF uses a locally installed open-source or licensed organization font (`MCIAS_ARABIC_FONT_PATH`), never a downloaded font. Real organization branding, formal Arabic layout acceptance and cross-platform font testing remain pending.
4. A real authenticated Arabic RTL browser frontend is included. Full production user-acceptance testing, beneficiary-statement print layout, institutional signature/watermark workflow, formal privacy review, key custody, external backup/restores, signed human gate approval and institution-approved golden datasets remain OPEN.
5. Local database admins can bypass owner-controlled database triggers; least-privilege PostgreSQL service accounts and independently controlled audit receipts are required.

Do not mark G7 ACCEPTED until tests have passed on a reproducible exact commit, referenced in GATE_STATUS.md, and approved by an authorized human.

## Interactive Arabic reporting UI

Run the on-premises API after local database migration:

```bash
python -m pip install -e '.[test]'
alembic upgrade head
uvicorn mcias.app:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/ui/reports** (the UI is initially a login form, **not** a demo with fabricated financial records). Sign in with a valid account and MFA when required. Tokens remain in volatile JS memory only, never localStorage/cookies or URLs. Re-loading the page requires a fresh login. Protected API endpoints enforce permissions regardless of UI state. No internet or CDN is needed.

The UI has four tabs: executive summaries separated by currency; masked claim-level financial rows and evidence counts behind `reports.details.read`; beneficiary statement using a POST JSON body with `reports.beneficiary.read` and `medical_fields.beneficiary_token.read`; and frozen report archive. Privileged staff may freeze a fully imported batch by explicit action if they have `reports.create` and `claims.read`.

Additional explorer endpoints:

| Method | URL | Role |
|---|---|---|
| GET | `/api/v1/report-explorer/snapshots?limit=20&offset=0` | `reports.read` |
| GET | `/api/v1/report-explorer/snapshots/{id}/entries?state=held` | `reports.details.read` + `reports.read` |

No original source columns, raw medical fields, names, diagnoses, or beneficiary tokens are returned from the explorer. The UI shows audit/governance evidence *summaries* only after the independent `claims.read` permission.

Downloads: `/api/v1/reports/snapshots/{id}/excel?lang=ar` (Arabic RTL) and `/api/v1/reports/snapshots/{id}/pdf?lang=ar` (local-font Arabic RTL). The `en` variant remains for compatibility. Original source worksheets require separate role plus **individual field authorization**, and the raw contents remain text-only to defeat Excel formula injection.

### Additional tests
- Browser: Arabic `lang` and `dir`, strict script/style CSP, asset allowlist, no-store and privacy checks.
- JS syntax: `node --check mcias/web_g7/dashboard.js` in CI.
- Arabic PDF: verified synthetic local-font rendering when the CI host supplies an eligible local font.
- Arabic Excel: RTL worksheet, original row strings and formula-like values remain literal.
- Real PostgreSQL: an imported synthetic batch, G5/G6 evidence, report generation, repeat idempotency, objection triggers immutable version 2, old report unaffected, SQL update trigger rejection, foreign tenant denied.

### G7 limitations
- Institutional medical data must **never** be committed to GitHub or synthetic CI fixtures.
- Default-deny permissions are intentionally not auto-granted. An organization administrator must configure roles through an approved RBAC setup; the UI cannot grant itself report access.
- A dashboard is a read-only representation of approved/held evidence, **not** an authorized payment order.
- Raw frozen JSON internally contains original source values for T18. Operational at-rest encryption, least-privilege DB accounts, and retention policy require independent on-prem acceptance.
- PostgreSQL snapshot isolation/performance for high load, multi-stage institutional signoff, RTL visual user-acceptance and actual private deployment have **not** been demonstrated.
