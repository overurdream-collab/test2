# MCIAS v2.0 — execution baseline (2026-10-10)

## Scope
Standalone on-premises installation per organization, PostgreSQL, local source store and AI; financial/administrative audit only. Original claim fields immutable. Professor OS → ReaderAgent → Palermo-1 → 8 agents + deterministic rule engine → Palermo-2 → human approval. Written organization-head approval required for contractual/exclusion changes even when activated by Super Admin.

## Current delivery status
G1 foundation scaffold started, not accepted. Current API only exposes liveness/readiness and a development-only guarded status route. There is **no production authentication**, MFA, RBAC enforcement, claim processing, approved schema migration or completed acceptance testing. Do not deploy with sample credentials.

## Gates (sequential estimate 48 weeks)
| Gate | Weeks | Deliverables | Exit |
|---|---:|---|---|
| G1 | 4 | PostgreSQL migrations, auth, MFA, RBAC, audit, backup | security and restore tests |
| G2 | 6 | ReaderAgent, provenance, quarantine, Palermo-1 | completeness and OCR tests |
| G3 | 4 | Contracts, tariffs, beneficiaries, temporal references | overlap and authorization tests |
| G4 | 6 | Batches, claims, attachments | import and resume tests |
| G5 | 8 | Eight agents, rule engine, Palermo-2 | no-double-deduction tests |
| G6 | 4 | Approvals, objections, selective re-audit | history and workflow tests |
| G7 | 4 | Excel/PDF, dashboards, statements | source integrity and privacy |
| G8 | 8 | Intelligence, analysis studio | evidence and false-positive review |
| G9 | 4 | Security, restore, release docs | signed production acceptance |

## Non-negotiable blockers
Contract precedence; accounting base and deduction order; rounding/currency; retention; target load; OCR quality threshold; medical field permissions. No production rule may invent these.

## Local development
1. Install Python 3.11+, Docker and dependencies: `pip install -e '.[test]'`.
2. Set a local `POSTGRES_PASSWORD` and `MCIAS_DATABASE_URL` in your environment.
3. Start PostgreSQL: `docker compose up -d db`.
4. Run unit tests: `pytest`.
5. Start API: `uvicorn mcias.app:app --reload`.
**Database tables are not migrated yet**; this is a scaffold, not a runnable end-to-end claims product.

## 2026-10-18 — binding future-scope amendment
See [unified inputs and audit Arabic requirements](MCIAS_UNIFIED_INPUTS_AUDIT_REQUIREMENTS_AR.md). All input kinds need append-only history/no deletion, effective-date reasoning, tenant boundaries, auditable actor/action, family-member analytics, and strictly reviewed contract clauses. Implement and test this scope separately; older historical delivery-status statements above are snapshots, not a current status certification.
