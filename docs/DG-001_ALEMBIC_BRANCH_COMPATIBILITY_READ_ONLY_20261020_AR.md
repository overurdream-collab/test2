# DG-001 — Alembic cross-branch migration compatibility (READ-ONLY)

**Date:** 2026-10-20. **Status:** CONFIRMED DIVERGENT REVISION CHAINS / DESIGN ONLY / NO DATABASE CHANGE.
**Scope:** PR #20 A1, PR #23 Contract Intelligence, PR #25 Unified Inputs; lineage includes PR #22 and main. Source files examined at the pinned Git SHAs below, not a merged checkout. No migrations, `alembic upgrade`, `stamp`, `merge`, `revision`, DB connection, or production schema change was performed.

## Authoritative snapshots
- main reference `b69defa2f621458ef44d790b510840307a81009a` (parent chain includes `alembic/versions/0018_claim_query_indexes.py`, revision `0018_claim_query_indexes`, parent `0017_operational_limits`). The same 0018 migration is present in inspected PR25.
- PR #20: `b536a94adf4d190ac48856bd435a8a624f3931f4` — **no Alembic migration in its changed-file inventory**. No direct migration collision; A1 still relies on schemas and input authority owned elsewhere.
- PR #22: `b694a2a1603a9a4c6d7af26ed56035b1a28b0166` — `alembic/versions/0019_reference_points.py` defines `revision='0019_reference_points'`, `down_revision='0018_claim_query_indexes'`; creates `reference_points` plus its closure history.
- PR #23: `39a4a9b93e9eb04ea7c09c8c155c3e08f38c6ec0` — has `0019_reference_points` as inherited ancestor and `alembic/versions/0020_contract_proposals.py`, `revision='0020_contract_proposals'`, `down_revision='0019_reference_points'`. Creates `contract_proposals`, `contract_proposal_reviews`, and `contract_proposal_promotions`; last references `reference_points.id`, and guards historical mutation with PostgreSQL trigger. Its `alembic/env.py` additionally imports model metadata for reference points/proposals.
- PR #25: `a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1` — contains `0019_input_clauses` inherited from its branch baseline, `revision='0019_input_clauses'`, `down_revision='0018_claim_query_indexes'`; its own `alembic/versions/0020_manual_contract_metadata.py` defines `revision='0020_manual_contract_metadata'`, `down_revision='0019_input_clauses'`. Adds nullable `contract_number`, `contract_notes` and unique constraint `uq_contract_number_version` to `contract_versions`.

## Exact divergent topology

```text
                        0018_claim_query_indexes (shared ancestor)
                                  |
               +------------------+-----------------------+
               |                                          |
     0019_reference_points                           0019_input_clauses
         (PR22/PR23)                                   (PR25 ancestry)
               |                                          |
     0020_contract_proposals                        0020_manual_contract_metadata
          (PR23)                                         (PR25)
```

**Confirmed conflict:** Two independent 0019 revisions branch from the same 0018; two different 0020 revisions build upon opposite parents. These are *distinct revision identifiers*, NOT the same Alembic revision ID duplicated; their human numerical prefixes overlap. If combined unchanged into a single migration directory, the graph has multiple heads and a naïve `upgrade head` cannot be treated as a verified linear deployment plan. PR23 also depends on `reference_points`, which PR25's 0019 does not create. Neither PR23 nor PR25 can substitute for the other's 0019 ancestry. This is not resolved by Git's file-level merge.

## Design-only resolution proposal; NOT EXECUTED
1. Obtain approval for a dedicated temporary integration branch from the exact then-current `main` HEAD. Freeze the tested parent PR SHAs. Do not cherry-pick all product code blindly.
2. Compare both 0019 implementations and all 0020 PostgreSQL constraints/FKs, existing 0018 lineage, ORM metadata and engine configuration. Retain BOTH durable history structures if product owners confirm they are independently required; do not delete or overwrite either prior migration. Decide a **single canonical ordered lineage or an explicitly reviewed merge revision** after checking the dependency graph and data model; do not choose from filename numbers alone.
3. Author a collision-free Alembic integration plan in that future authorized branch, including revision dependencies and compatibility with deployed revision stamps. PR23's `contract_proposal_promotions.reference_point_id` must resolve to an actually created `reference_points` table. PR25's manual metadata requires `contract_versions` and its version uniqueness semantics. Resolve branch-inherited `alembic/env.py` metadata differences, test PG-only triggers and constraints.
4. Before any production or branch merge: on disposable PostgreSQL 16 only, test `alembic heads`, `alembic history`, offline SQL generation, fresh-schema `upgrade head`, repeated no-op upgrade, existing-database transition from each historical head, revision stamp validation and negative data/immutability regression. Do not mark `SKIP` of required checks as PASS. Check migration collision and coexistence of relevant old/new tables, constraints, triggers, and both models.
5. Stop on first proven incompatibility. Record exact source SHA, conflicting revision, error, proposed minimal migration-only resolution and new CI, for independent owner approval. No automatic downgrade or destructive rewrite of existing history.

## Read-only acceptance decision
- **Verified:** textual/source-level conflicting ancestry and dependencies; neither PR #20 nor the current standalone passing CI validates the combined Alembic graph.
- **Not verified:** composed Alembic `heads`, `upgrade`, online/offline migrations, PostgreSQL compatibility of the combined branches, deployed schema stamp lineage. No such integration CI was executed for this report.
- **Risk:** cross-branch integration is BLOCKED pending explicitly approved migration-compatibility plan; the standalone PR CI acceptance results remain scoped to their individual SHAs.
- **Restrictions:** DOCUMENTATION CORRECTION & READ-ONLY INTEGRATION DESIGN ONLY; NO MERGE, NO MIGRATION, NO DB WRITE, NO DEPLOY, NO PROD.

## SHA freshness and handoff
The initial PR25 source SHA above identifies **the inspected source snapshot**. This documentation file is a new Git commit, so the new PR25 HEAD requires separate CI verification; earlier passing runs cannot be transferred to the documentation SHA without matching head_sha. History and failed source-model measurements must remain intact.
