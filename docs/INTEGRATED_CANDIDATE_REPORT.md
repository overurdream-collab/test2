# Integrated candidate implementation report

This engineering candidate combines frontend PR #11 at f026862 and G9 PR #10 at
c7a6eedef47887a9fa1a25b32a4a42ff15bf806a on `feat/mcias-integrated-candidate`.
No protected branch is merged, no external environment is deployed, and no
institutional gate is accepted.

## Completed

- Combined G9 production docs restrictions/headers, backup/restore hardening,
  preflight, release receipts, deployment harness and frontend package assets.
- Corrected raw-ingestion field authorization, rejection duty separation and
  historical proposer conflict after intervening holds; negative regression tests.
- Corrected container health variable expansion and excluded new build/test caches
  from the Docker context. Compose configuration validates with synthetic files.
- Added real PostgreSQL/browser lifecycle: enrolled administrator MFA, original
  upload/extraction, source hashes/duplicates, malformed quarantine and encrypted
  original recovery, UI staging/confirmed import, linked evidence, audit inspection,
  independent approval, frozen reports/export denial, evidenced objection and
  re-audit request with action audit events.
- Added clean-commit source/archive handoff, reviewed-wheel receipt, SHA-256
  inventory and tests excluding ignored credentials and rejecting committed keys.
- Added Arabic external-installation/test instructions and role-based UAT checklist.

## Local verification

- **322 Python tests passed, zero skipped**, on fresh PostgreSQL 16, including G9
  least-privilege SQL negative tests and actual encrypted backup/restore drill.
  13 inherited framework/deprecation warnings remain.
- **10 JavaScript tests passed**; modules pass syntax and Python compile checks.
- **59 workspace routes** pass responsive Arabic/English, both themes, keyboard,
  evidence/dialog/session checks; **zero page errors or automated WCAG violations**
  on audited views. Separate real login/read/logout browser checks pass.
- The new **seven-stage synthetic lifecycle** passes with no page errors using
  Chromium → actual FastAPI → PostgreSQL. Its G5 audit is an explicitly synthetic
  backend-engine/Palermo-2 fixture seam, because production audit HTTP execution
  remains unavailable. It does not certify production financial activation.
- Runtime wheelhouse built using the installed test-environment version constraints;
  clean virtualenv offline installation and `pip check` pass. Installed wheel
  imports and enterprise assets verified from outside the source checkout.
- Source/evidence logs and hashes are under `docs/evidence/integrated`. CI attaches
  exact-head results and downloadable synthetic evidence to the integration PR.

## External validation still required

Follow [Arabic handoff](INTEGRATED_CANDIDATE_HANDOFF_AR.md),
[UAT](INTEGRATED_UAT_AR.md), [security review](INTEGRATED_SECURITY_REVIEW.md),
[route/API coverage](FRONTEND_ROUTE_API_MATRIX.md) and existing G9 acceptance tracker.
The target host must demonstrate TLS, production runtime SQL grants, local scanner,
key custody/rotation, host security, load/concurrency and a witnessed restore.
Institutional financial/privacy policies and signed G0–G9 approval remain open.
Backend capability gaps documented in the frontend matrix remain gaps; they were
not silently implemented or relabeled as operational by integration work.

The bundled wheelhouse is for Python 3.12/Linux x86_64; different target versions
or architectures require compatible reviewed wheels. Source hashes/checksums need
an independently trusted receipt, and do not constitute a signature or acceptance.
