# MCIAS — mandatory instructions for Codex, other agents, and human engineers

This repository is a **medical-insurance claims audit** project. Any change must
be traceable and safe. Before you read, edit, test, save, commit, review or hand
off work, follow these instructions. Source of truth:

- docs/engineering/TRACEABILITY_POLICY_AR.md (binding documentation policy)
- docs/engineering/INDEX.md (documentation index)
- docs/engineering/HANDOFF_A1_AR.md (step-by-step instant handoff)
- docs/engineering/worklogs/A1_2026-10-17.md (GitHub-backed event history)
- docs/agents/A1_INVOICE_INTEGRITY.md (A1 design and limitations)
- docs/agents/A1_EVIDENCE_REPORT_20261017.md (all tests, including failures)

## Non-negotiable operational process

1. Identify the request, repo, branch, parent SHA, approved scope and data
   classification **before any operation**. Keep a worklog event for each
   substantive action: inspections, research, decisions, edits, tests, failures,
   CI, PR edits, delivery. Group only closely related read-only inspections,
   listing every source; do not invent historical events.
2. Every non-worklog file change MUST be committed **atomically with a new
   event added under docs/engineering/worklogs/**. Write the exact full
   parent SHA in the new event's before_sha field and after_ref: SELF.
   Record actor, timestamp or honest unknown, files, reason, command, actual
   outcome, tests, evidence, risks, rollback and precise next step. Run
   python scripts/check_traceability.py; it enforces this after the baseline.
3. For every test, distinguish PASS, FAIL, NOT_RUN, SKIPPED, CANCELLED;
   bind findings to the **exact tested SHA**, commands, dataset and CI run.
   Never claim a model accuracy based on an unmeasured number or another
   model's output. Preserve failing cases and false positives.
4. For every handoff, update docs/engineering/HANDOFF_A1_AR.md if decisions,
   architecture, evidence, open blockers, commands or endpoints have changed.
   Leave an explicit next action; no undocumented "done".
5. Never place passwords, tokens, PHI, or real patient records in Git logs,
   third-party services, model prompts or CI. Synthetic data only.
6. Do NOT modify or merge main without explicit permission, do NOT work on A2,
   and do NOT run paid services or destructive operations. PR #20 remains
   Draft. Do not reject/approve claims or make automatic financial deductions.
7. The A1 model is real locally run Qwen3-8B plus independent Decimal/evidence
   guards, but institutional acceptance and production deployment remain
   OPEN. Source-attestation and G3/G4 unit semantics require independent
   verification. See evidence report for genuine failures and retests.

## Before claiming success
Read the exact GitHub Actions runs at the PR head. A green CI only proves
those tests passed, not deployment fitness. If something could not be
tested or observed, explicitly say it was NOT_RUN/UNKNOWN and why.

This AGENTS.md is included in the unmerged A1 feature branch. It is not
currently a rule applied to main until formally accepted and merged.
