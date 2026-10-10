# G7 — Versioned Reporting (engineering delivery)

Status: **IMPLEMENTED FOR SYNTHETIC ENGINEERING TESTS / OPEN FOR INSTITUTIONAL ACCEPTANCE.** This work is based on G5/G6 engineering code and is not a waiver of G0–G6 acceptance or the pending MCIAS policy pack.

## Components
- \`0014_g7_reporting\`: PostgreSQL append-only \`report_snapshots\`, unique \`(batch_id,version)\`, database trigger checks active same-organization actor and batch. No destructive downgrade.
- \`reporting_g7.py\`: approved/held derivation from latest G5 audit snapshot and versioned G6 governance decision, strict per-currency Decimal totals, frozen SHA-256, old-version stability and source-column retention. Only completely imported batches are currently eligible; no silent partial import.
- \`report_exports_g7.py\`: Excel executive summary, permission-gated original-source worksheet, PDF aggregated executive report without patient identifiers. Original Excel strings are marked text to avoid Excel formula injection or numeric-identifier coercion.
- \`reporting_g7_api.py\`: protected version creation, summary/dashboard JSON, Excel, PDF, beneficiary statement. No source-value API is available to a user without extra \`reports.originals.export\` permission **and** an individually authorized \`medical_fields.<column>.read\` permission for every column.
- Source rows and document SHA-256 are copied into frozen snapshots for T18 provenance; no raw claim edit takes place.
- Reports do not assign insurance liability to held, objected, unverified or unreconciled items.

## API (all require bearer authentication; permissions default deny)
| HTTP | Endpoint | Required |
|---|---|---|
| POST | \`/api/v1/reports/batches/{batch_id}/snapshots\` | \`reports.create\`, \`claims.read\` |
| GET | \`/api/v1/reports/snapshots/{report_id}\` | \`reports.read\` |
| GET | \`/api/v1/reports/snapshots/{report_id}/dashboard\` | \`reports.read\` |
| GET | \`/api/v1/reports/snapshots/{report_id}/excel\` | \`reports.export\` |
| GET | \`/api/v1/reports/snapshots/{report_id}/excel?include_originals=true\` | above + \`reports.originals.export\` + every column medical-field permission |
| GET | \`/api/v1/reports/snapshots/{report_id}/pdf\` | \`reports.export\` |
| GET | \`/api/v1/reports/snapshots/{report_id}/beneficiaries/{token}/statement\` | \`reports.beneficiary.read\`, \`medical_fields.beneficiary_token.read\` |

The \`dashboard\` endpoint provides safe metrics for a future RTL UI; an interactive frontend has not been delivered here. Reports are created explicitly by authorized staff and do not imply payment authorization.

## Tests
Run \`python -m pytest -q tests/test_g7_reporting.py tests/test_g7_postgres.py\` under the CI PostgreSQL environment, plus full regression.
- **T13:** frozen version 1 does not change when a later G5 result arrives.
- **T18:** original columns, strings such as \`0012300\`, and literal cells beginning with \`=\` remain intact.
- **T20:** approved and held totals reconcile independently per currency, and unauthorized sensitive originals are denied.
- Other cases: open objections zero payable; malformed G5 amount held; cross-tenant mixing denied; tampering detected; invalid or partial batches blocked.

## Important outstanding controls
1. An institution must approve financial rules, report format and which fields require elevated access. Default-deny protects against unapproved use.
2. The 10,000-claim in-memory ceiling is a provisional engineering guard, not an approved workload/SLA. Realistic stress tests, streaming and snapshot transaction-isolation assurance are pending.
3. PDF is currently an English-only synthetic executive template. Arabic shaping, licensed local Arabic font, right-to-left report design and real organization branding remain to be implemented before an Arabic production release.
4. End-to-end secured frontend, beneficiary-statement print layout, signature/watermark workflow, formal privacy review, key custody, external backup/restores, signed human gate approval and institutional golden datasets remain OPEN.
5. Local database admins can bypass owner-controlled database triggers; least-privilege PostgreSQL service accounts and independently controlled audit receipts are required.

Do not mark G7 ACCEPTED until tests have passed on a reproducible exact commit, referenced in GATE_STATUS.md, and approved by an authorized human.
