# Consolidated engineering baseline on main

User authorization: consolidate the implementation into main, retire old branch work, and run CI on main.

Integrated source baseline: `0617ce2e8674553128779c1763f8982f43d50c12` from `feat/mcias-operational-controls` (PR #13). Exact-head CI passed all nine checks; primary run 38087773682 recorded 336 Python tests plus a separate successful Seed integration test, 10 JavaScript tests, 59 browser routes and successful lifecycle/retention workflows. Full suite skips Seed only because it is run in the dedicated preceding step. No test totals are summed across duplicate workflows.

## Incorporated branches

The baseline contains the complete Git ancestry of g1-foundation, g2-ingestion, g3-reference, g4-claims-batches, g6-governance, g5-g6-g7-reporting, g8-intelligence, g9-release-hardening, mcias-premium-enterprise, mcias-integrated-candidate and mcias-operational-controls. Their engineering deliverables are consolidated without pretending all routes have operational backends.

## Superseded branches

- feat/g5-audit-engine: the operational G5 baseline is included through the later G6/reporting track. This branch additionally contains isolated G6/G7 preparatory pure-Python prototype modules, not wired to the operational API. They are preserved in archive refs; not copied into the current application as competing governance/report engines.
- feat/g6-governance-preparatory: uses alternate governance model/module names and an alternate 0013 migration. The current governance_g6 implementation and authoritative migration are retained to avoid two incompatible schemas or regressions in authorization.
- feat/mcias-ui-workspace: earlier six-section UI superseded by the tested two-interface enterprise workspace. Its additional /ui/workspace shell is not exposed alongside the replacement.

Before old remote feature branches are removed, their exact heads are preserved as annotated `archive/main-consolidation/...` tags. GitHub PR records and discussions remain available. Contained requests are completed/closed by GitHub where applicable; superseded requests are closed as superseded, not inaccurately represented as merged.

## CI and acceptance

ci.yml already runs on main. g8.yml, g9.yml and workspace.yml now also run on main. Enterprise CI packages the committed source and runtime wheels on main. No deploy step, external clinical transfer, automatic financial-policy activation or institutional gate signature is added.

Merge only after the consolidation PR's exact head passes CI. After merge, verify the main push workflows, then retire old PRs/remote feature branches. The merge record and CI URLs provide the final evidence. Keep main's gate status OPEN/NOT ACCEPTED and perform the external synthetic acceptance run before production use.
