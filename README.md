# MCIAS v2.0

## MCIAS v2.0 — authoritative implementation handoff (PR #22, DRAFT)

**For any new engineer, Codex or reviewer, start here:**

1. [MCIAS v2.0 developer guide (Arabic)](docs/MCIAS_V2_DEVELOPER_START_HERE_AR.md) — architecture, file map, versioned clauses, G3/G5 reconciliation, four outputs, APIs and safe workflows.
2. [Chronological implementation journal](docs/MCIAS_V2_EXECUTION_JOURNAL_AR.md) — each engineering step, tests, regressions, decisions, evidence and remaining blockers.
3. [Feature-by-feature acceptance and tests](docs/MCIAS_V2_ACCEPTANCE_MATRIX_AR.md) — implemented vs partial vs unimplemented and the precise acceptance criteria.
4. [Prior handoff](docs/REFERENCE_POINTS_AND_OUTCOMES_HANDOFF_AR.md), [Agent architecture draft (PR #19)](https://github.com/overurdream-collab/test2/pull/19), [PR #22 review](https://github.com/overurdream-collab/test2/pull/22).

**Important:** PR #22 is a standalone draft; until merged its files are on the `feat/temporal-reference-inputs-and-four-outcomes` branch only. It adds temporal reference input points and a **read-only** cross-check against existing G3/G5 financial authority; it does not automatically activate extracted clauses, update approved tariffs, or adjudicate medical/fraud findings. Four CSV outputs are provisional audit triage, not final insurer rejections or payment permissions. Institutional G0–G9 acceptance remains OPEN.

---

Official implementation repository. On-premises medical claims financial and administrative audit.

## Status
The integrated engineering baseline is maintained on **main**: security/authentication, ingestion, reference data, claims, audit, governance, reporting, intelligence, enterprise RTL/LTR interfaces, release tooling and operational controls. Backend/UI coverage and unavailable capabilities are documented in `docs/FRONTEND_ROUTE_API_MATRIX.md` and `docs/OPERATIONAL_CONTROLS.md`. Every production acceptance gate remains OPEN until institutional authorization and signed acceptance. Synthetic CI success is not production certification.

## Binding constraints
- Separate local PostgreSQL database and document storage per organization.
- Original claims and source files immutable; full provenance and quarantine.
- ReaderAgent -> Palermo-1 -> eight audit agents and deterministic rules -> Palermo-2 -> human approval.
- No external transmission of sensitive records; no autonomous medical or fraud judgments.
- Contract/exclusion activation requires written organization-head approval and Super Admin activation.

See `docs/IMPLEMENTATION_PLAN.md` for acceptance gates and policy blockers.

## G5 → G6 → G7 implementation track

See `docs/G5_G6_G7_ENGINEERING_HANDOFF.md` and `docs/G7_IMPLEMENTATION.md`. Generate only synthetic or institution-authorized development reports. The `/api/v1/reports` endpoints are permission-gated, and original medical columns are denied without individual field permissions. This engineering baseline is not a production deployment.

## G7 browser quick start (engineering)

```bash
python -m pip install -e '.[test]'
# Configure a local PostgreSQL URL and service credentials, then:
alembic upgrade head
uvicorn mcias.app:app --host 127.0.0.1 --port 8000
```

Go to **http://127.0.0.1:8000/ui/reports**. The right-to-left dashboard requires authenticated institutional users; no sample passwords or synthetic payouts are preloaded. Reports, redacted claim drilldown, the Arabic Excel/PDF exports and beneficiary statements are gated by server permissions. PDF typography requires a locally installed Arabic TTF (optional `MCIAS_ARABIC_FONT_PATH`). **No production enablement** until official gate signoff.

G7 tests: `python -m pytest -q tests/test_g7_reporting.py tests/test_g7_web.py tests/test_g7_integration.py`. Run the PostgreSQL integration suite using `MCIAS_TEST_DATABASE_URL` and GitHub Actions for exact evidence.

## G8 — Review-only Intelligence and Analysis Studio

The **G8 engineering branch** adds the on-premises Arabic analysis interface at
`http://127.0.0.1:8000/ui/intelligence`. It operates on immutable G7 report
versions with G4 source provenance, and offers historical aggregates, safeguarded
signals for human review, purely hypothetical financial scenarios and governed
versioned custom indicators. Task configurations require server-run synthetic
positive/negative checks and independent human activation; source roles are
default-deny. False-positive review events are append-only.

Local development (never production activation):

```bash
python -m pip install -e '.[test]'
alembic upgrade head
python -m pytest -q tests/test_g8_intelligence.py tests/test_g8_studio.py tests/test_g8_reviews.py tests/test_g8_web.py
uvicorn mcias.app:app --host 127.0.0.1 --port 8000
```

For PostgreSQL tests use the separately configured `MCIAS_TEST_DATABASE_URL`.
See `docs/G8_IMPLEMENTATION.md`, `docs/G0_G8_ACCEPTANCE_TRACKER.md` and the
draft G8 PR. All G0–G8 **institutional signed acceptance remains OPEN**.

## Enterprise administration and institution interfaces

The `feat/mcias-premium-enterprise` feature (stacked on G8) adds Arabic RTL /
English LTR enterprise workspaces at `/admin/dashboard` and
`/institution/dashboard`, with dark/light themes and authorized evidence views.
All unavailable backend modules are labeled, and all gates remain unaccepted.

- [Installation and on-premises deployment](docs/FRONTEND_INSTALLATION.md)
- [Complete frontend route/API coverage](docs/FRONTEND_ROUTE_API_MATRIX.md)
- [Design system](docs/FRONTEND_DESIGN_SYSTEM.md)
- [Implementation and verification report](docs/FRONTEND_IMPLEMENTATION_REPORT.md)
- [Synthetic screenshots of both interfaces](docs/previews/README.md)

## Integrated engineering candidate

Frontend + G9 are combined on `feat/mcias-integrated-candidate` for synthetic external
validation. See [implementation report](docs/INTEGRATED_CANDIDATE_REPORT.md),
[Arabic handoff](docs/INTEGRATED_CANDIDATE_HANDOFF_AR.md),
[security fixes](docs/INTEGRATED_SECURITY_REVIEW.md) and
[role-based UAT checklist](docs/INTEGRATED_UAT_AR.md). No G0–G9 approval is implied.

### Operational controls and synthetic test tools

See [operational controls](docs/OPERATIONAL_CONTROLS.md) and [retention policy](docs/RETENTION_POLICY.md).
New dedicated test seed references use `SYN-`; UUID primary keys are retained.
Seed CLI refuses production and non-`*_e2e` databases. Existing synthetic data is
not backfilled or relabeled. Production starts with a clean database. Archival is
local and encrypted; the proposed seven-year policy and any purge remain blocked
pending institutional approval.

### Consolidated main and continuous integration

`main` is the integrated engineering baseline, not institutional production acceptance. All four CI workflows run on pushes to `main`, including PostgreSQL regression, dependency checks, browser/accessibility checks and portable test packaging. See [branch consolidation](docs/MAIN_CONSOLIDATION.md) for incorporated and superseded branches.

## Bilingual policy and external acceptance pack

[العربية](docs/ACCEPTANCE_PACK_INDEX.md) · [English](docs/ACCEPTANCE_PACK_INDEX_EN.md): 13 proposed financial decisions, deployment checks, external test/report templates, UAT and independent penetration-test scope. All external results/signatures remain unexecuted; these documents do not authorize production.
