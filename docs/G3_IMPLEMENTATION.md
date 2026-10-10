# G3 — Reference management implementation and acceptance evidence

## Executable scope
- Contract versions and effective periods; provider tariffs with NUMERIC(18,4) and strict currency validation.
- Beneficiary categories and effective-date enrollments with tenant-scoped eligibility.
- Migration 0007 reference schema and migration 0008 PostgreSQL GiST exclusion constraints, immutable approved contract/tariff triggers, and cross-tenant enrollment guard.
- G3 lifecycle endpoints: create draft, attach written authorization, add tariffs, CSV preview/atomic import, create category/enrollment, eligibility, impact analysis, independent precedence/impact reviews, approval, and active-contract lookup.
- T04 rejects approved overlapping provider contract periods at service and database levels, including concurrent transactions.
- T05 reports retroactivity and conflicting contract versions; no historical financial adjustment is made. Retroactive non-overlapping contracts need a separate recorded reviewer before activation.
- Written authorization must come from a distinct, active same-tenant approver; production requires the G1 Ed25519 head-of-organization registry. Precedence policy review must be documented by a separate actor. Approval requires another actor and full RBAC.
- Approved contracts and tariffs are immutable, revisions are new versions, and all privileged actions generate audit events.
- CSV tariff import validates every row and either applies all rows atomically or none; original import bytes are not persisted by this reference API. Source-file provenance for approved tariffs must be supplied via the governed G2 pipeline when required by local policy.

## Production policy blockers
- A real organization must adopt and sign its own contract precedence policy. Software intentionally does not invent legal/financial precedence.
- A real written authorization with valid signature, organization head trust registry, and local permissions must be provisioned before production approval.
- Final monetary impact of retroactive reference changes requires G4/G5 claims and deterministic financial engine; G3 only identifies affected contract versions and requires explicit review.
- Gate signoff cannot be self-approved by an AI coding agent; G1/G2 acceptance and human G3 review remain prerequisites.

## Acceptance checks
- Run `python -m pytest -q` on G3 branch.
- Run PostgreSQL integration and restore drill against Alembic head `0008_g3_guards`.
- Run `tests/test_g3_reference.py`, `tests/test_g3_lifecycle.py`, `tests/test_g3_postgres_guards.py`, `tests/test_g3_api_security.py`, and `tests/test_g3_tariff_import.py`.
- Record CI run, exact head SHA, outcome, approved policy and signoff in gate evidence. A passing CI alone does not mean production accepted.

G3 is a functional implementation candidate; its gate remains OPEN pending external policy, real deployment verification, and human signoff.
