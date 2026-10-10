# G5 — Audit Engine | implementation and gate evidence

**Gate: OPEN / NOT ACCEPTED.** Work on this preparatory branch does not waive the binding G1–G4 signoff prerequisites.

## Delivered
- Pure deterministic Decimal engine with explicit approved financial policy, currency, precision, rounding and fixed deduction sequence.
- Eight evidence-producing administrative/financial checks: eligibility, tariffs, contract, exclusions, caps, cost sharing, duplicates and attachments.
- Palermo-2 independent reconciliation; unresolved findings hold results.
- Immutable G5 audit snapshots linked to G4 claims, source, actor and exact policy fingerprint; PostgreSQL insert/tenant and update/delete guards.
- Read-only, RBAC-protected audit evidence API. **No public endpoint accepts client-supplied financial policies.**
- Synthetic T08/T09 golden cases, regression and PostgreSQL migration tests.

## Critical blocked items
1. Organization must sign deduction order, accounting base, cap semantics, exclusions, cost-share basis, currency and rounding policy. The current sequence is a **test fixture**, not an institutional approval.
2. An authenticated, signed policy registry, lifecycle and service entrypoint must be approved before production audit execution. The internal `run_audit` function requires an explicitly approved policy; the API intentionally exposes read-only evidence.
3. Financial agents are deterministic evidence checks, **not AI clinical judgments**. Additional governed rule catalogs and realistic cross-claim caps are required for full eight-agent institutional scope.
4. Real-world T08/T09 golden claims, reconciliation with institution-signed expected values, high-volume throughput, interruption/concurrency tests and G1–G4 signed gates remain pending.

## Evidence
- CI: GitHub Actions on `feat/g5-audit-engine`; record exact successful SHA and run URL before acceptance.
- Tests: `python -m pytest -q tests/test_g5_engine.py tests/test_g5_postgres.py`.
- Required signoff: named organization approver and independent reviewer; never infer acceptance from passing CI.

## Additional hardening and synthetic validation
- Draft policies are explicitly marked unauthorized and cannot become approved by using the draft helper.
- Internal audit orchestration now rejects missing policy authorization before any database access; it remains **non-production** until a trusted signed-authorization verifier is integrated. Do not treat caller-supplied verification flags as cryptographic proof.
- Added seeded 1,000-case Decimal arithmetic regression covering varying exclusions, tariffs, caps, copays and independent Palermo-2 verification.
- No real patient data, real claims, or institutional approval is implied by these tests.
- Activation, signed-policy trust chain, end-to-end full batch processing, advanced policy catalog and real-scale load testing remain blockers; do not mark G5 ACCEPTED.
