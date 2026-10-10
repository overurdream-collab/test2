# MCIAS v2.0

Official implementation repository. On-premises medical claims financial and administrative audit.

## Status
G5/G6 hardening and G7 reporting engineering are present on this **feature branch**, but every production acceptance gate remains OPEN until institutional authorization and signed acceptance. Synthetic CI success is not production certification.

## Binding constraints
- Separate local PostgreSQL database and document storage per organization.
- Original claims and source files immutable; full provenance and quarantine.
- ReaderAgent -> Palermo-1 -> eight audit agents and deterministic rules -> Palermo-2 -> human approval.
- No external transmission of sensitive records; no autonomous medical or fraud judgments.
- Contract/exclusion activation requires written organization-head approval and Super Admin activation.

See `docs/IMPLEMENTATION_PLAN.md` for acceptance gates and policy blockers.

## G5 → G6 → G7 implementation track

See `docs/G5_G6_G7_ENGINEERING_HANDOFF.md` and `docs/G7_IMPLEMENTATION.md`. Generate only synthetic or institution-authorized development reports. The `/api/v1/reports` endpoints are permission-gated, and original medical columns are denied without individual field permissions. This branch is not a production deployment.

## G7 browser quick start (engineering)

```bash
python -m pip install -e '.[test]'
# Configure a local PostgreSQL URL and service credentials, then:
alembic upgrade head
uvicorn mcias.app:app --host 127.0.0.1 --port 8000
```

Go to **http://127.0.0.1:8000/ui/reports**. The right-to-left dashboard requires authenticated institutional users; no sample passwords or synthetic payouts are preloaded. Reports, redacted claim drilldown, the Arabic Excel/PDF exports and beneficiary statements are gated by server permissions. PDF typography requires a locally installed Arabic TTF (optional `MCIAS_ARABIC_FONT_PATH`). **No production enablement** until official gate signoff.

G7 tests: `python -m pytest -q tests/test_g7_reporting.py tests/test_g7_web.py tests/test_g7_integration.py`. Run the PostgreSQL integration suite using `MCIAS_TEST_DATABASE_URL` and GitHub Actions for exact evidence.
