# MCIAS G8 — Intelligence, Analysis Studio, Review Signals and Scenarios

**Engineering branch:** `feat/g8-intelligence` (stacked on `feat/g5-g6-g7-reporting`).
**Gate status:** **OPEN / NOT ACCEPTED**. These features do not bypass G0–G7 formal human acceptance or activate institutional financial policy.

## Scope delivered for engineering verification

1. Historical and comparative descriptive analytics from frozen G7 report snapshots, grouped by **provider**, **service code** or **calendar month**, with isolated currencies, exact Decimal reconciliation and G4 source integrity checks.
2. Privacy floor: identifiable provider/service/month groups with fewer than **5** records are combined into an unlabeled suppressed group; if the combined group is still below 5, its financial values are hidden. Hypothetical scenario financial values are also withheld for currencies with fewer than 5 approved claims. Cohorts smaller than twice the minimum group size cannot produce statistical signals. A count, numerator, denominator, baseline and threshold accompany each signal.
3. **Review-only statistical signals**: held-claim rate or provider claimed-amount share. They do **not** classify a doctor, patient, insurer or provider as fraudulent and cannot generate a clinical judgment, payout, claim status, deduction or policy change.
4. **What-if** simulation: a caller explicitly selects a hypothetical percentage reduction of approved payable amounts. Exact per-currency baselines and hypothetical differences are displayed. No financial write-back, hidden rounding convention or policy mutation.
5. Versioned **Analysis Studio**: an authorized technical owner creates a new immutable version with exactly five whitelisted settings (approved source, indicator, dimension, percent threshold, minimum group size). A server-side synthetic 20-record positive/negative-control test writes an immutable evidence event. A **different human reviewer** must explicitly activate it; inactive or untested tasks cannot run (**T19**). Deactivation is append-only; a successor version cannot activate while its predecessor is still active.
6. Independent signal assessments (**false positive**, **needs follow-up**, **insufficient evidence**) use a coded reason without medical free text, an independent actor, immutable version history and the fingerprint of the exact signal. False-positive rate is reported using the **number actually reviewed** as denominator, not all claims or all signals. This measures reviewer feedback, not true fraud prevalence.
7. Persisted analysis results include source report IDs/fingerprints, configuration, evaluation, creator and SHA-256. PostgreSQL enforces append-only updates/deletes, same-org actor/source references and separation from the original G4/G5/G6/G7 records.
8. Same-origin Arabic RTL interface at `http://127.0.0.1:8000/ui/intelligence` with four areas: historical overview, review signals and feedback, what-if scenarios and task governance. No CDN, inline JS, token persistence, client-side custom queries or fabricated production numbers.

## API and permissions

All endpoints require an authenticated user in the same tenant, plus a server-side RBAC entitlement. There is **no default grant**.

| Method | Endpoint | Permission |
|---|---|---|
| GET | `/api/v1/intelligence/capabilities` | `intelligence.read` |
| GET | `/api/v1/intelligence/studio/tasks` | `intelligence.studio.read` |
| POST | `/api/v1/intelligence/studio/tasks` | `intelligence.studio.manage` |
| POST | `/api/v1/intelligence/studio/tasks/{id}/test` | `intelligence.studio.test` |
| POST | `/api/v1/intelligence/studio/tasks/{id}/activate` | `intelligence.studio.activate`, different from creator and tester |
| POST | `/api/v1/intelligence/studio/tasks/{id}/deactivate` | `intelligence.studio.activate` |
| GET | `/api/v1/intelligence/studio/tasks/{id}` | `intelligence.studio.read` |
| POST | `/api/v1/intelligence/runs` | `intelligence.run` **and** `reports.read` |
| GET | `/api/v1/intelligence/runs` and `/runs/{id}` | `intelligence.read` |
| POST | `/api/v1/intelligence/runs/{id}/signals/{index}/reviews` | `intelligence.review`, different from run creator |
| GET | `/api/v1/intelligence/runs/{id}/review-summary` | `intelligence.read` |

A G8 analysis run references **one to twelve distinct frozen G7 reports**, from **different G4 batches**, with no more than **10,000 claims** as an unapproved *engineering safeguard*. These are not agreed production workload thresholds. Requests cannot send raw SQL, Python code, agent prompts, external URLs, LLM commands, clinical identifiers, or unapproved source types. Allowed source is only `g7_frozen_report_snapshots`.

**Example request for descriptive analysis:**

```json
{
  "kind": "summary",
  "report_ids": ["<frozen-G7-report-UUID>"],
  "parameters": {"dimension": "provider", "min_group_size": 5},
  "task_id": null
}
```

**Example Studio task configuration:**

```json
{
  "code": "provider_hold_rate",
  "configuration": {
    "source": "g7_frozen_report_snapshots",
    "indicator": "hold_rate",
    "dimension": "provider",
    "threshold_percent": "60",
    "min_group_size": 5
  }
}
```

For `kind=signals`, send the ID of a previously **tested and independently activated** task, and an empty `parameters` object. The server resolves the immutable configuration. `kind=simulation` requires an explicit `reduction_percent`; results are review-only and do not affect claims.

## Acceptance evidence and outstanding requirements

- **T14**: synthetic positive/negative controls, boundary thresholds, suppression of low-count categories, numerator/denominator and false-positive review quality with explicit reviewed-only denominators. **Pending:** institutional labeled data, independent clinical/financial audit of false positives and agreed alert thresholds.
- **T15**: unauthorized roles, foreign tenants, medical/raw field access, unapproved data sources, arbitrary fields/SQL and forged report references denied. **Pending:** penetration test, target hardware key custody and security signoff.
- **T19**: no untested/unauthorized task activation, separate reviewer, immutable task versions and changes, server-verified test result, deactivation and prevention of parallel active versions. **Pending:** institution-specific reviewer authority registry and signed organizational acceptance.
- **Traceability**: G4 immutable metadata tied to frozen G7 source hash, independent G8 reconciliation, versioned G8 runs, review decisions stored in PostgreSQL. **Pending:** production-source handling, true baseline denominators across organizations/time periods, operational performance and backups.
- **Human approval**: this is a draft code implementation, **not an accepted G8 gate or production intelligence release**. All former G0–G7 acceptances remain tracked separately in `docs/G0_G8_ACCEPTANCE_TRACKER.md`.

## Local development

```bash
python -m pip install -e '.[test]'
alembic upgrade head
python -m pytest -q tests/test_g8_intelligence.py tests/test_g8_studio.py tests/test_g8_reviews.py tests/test_g8_web.py
uvicorn mcias.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/ui/intelligence` with an institution-provisioned account with only the roles needed. Set `MCIAS_TEST_DATABASE_URL` for the separate PostgreSQL integration suite. Do not commit real patient data, insurance claims or signing secrets. **G8 and earlier gates remain non-production pending written signoff.**

## Last verified reproducible engineering run (before human acceptance)

- Commit: `7efa4515e1bbc9ea146b3c9a55bc56f97173d7e0`.
- Full inherited regression: [CI run 38062833679](https://github.com/overurdream-collab/test2/actions/runs/38062833679) — **216 passed, 16 skipped** unit tests; **143 passed** PostgreSQL integration tests; dependency audit success.
- G8-specific: [CI run 38062830731](https://github.com/overurdream-collab/test2/actions/runs/38062830731) — **29 passed** unit/security/UI tests; **3 passed** PostgreSQL tests, including a synthetic frozen G7 report -> audited G8 analysis -> activated Studio signal -> independent review.
- JavaScript syntax and wheel asset packaging are tested in the G8-specific pipeline. Successful synthetic CI remains distinct from institution-specific quality review and signature.

## Operational privacy controls beyond k-anonymity

A user needs **both** `intelligence.run` and `reports.read` to generate any analysis, so the G8 endpoint cannot be used to bypass access controls for the underlying G7 report. It never exposes `source_values`, beneficiary tokens, source-page locators or patient records. Medical source fields are not allowed as dynamic dimensions or expressions. The specific reviewer permission `intelligence.review` is required to enter a false-positive or further-review disposition; the author of the signal cannot review their own signal. The source report and reviewer events remain immutable.
