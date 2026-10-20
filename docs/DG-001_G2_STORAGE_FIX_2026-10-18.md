# DG-001 — G2 encrypted storage test-fixture repair

Date: 2026-10-18. PR #25 contracts-only. Parent: d92b1d7a97af98e46a8de99540d7246ee6be8355.
Evidence: https://github.com/overurdream-collab/test2/actions/runs/39076860021
Observed Chromium: both writer and reader reached contracts, RBAC marked PASS, upload UI displayed generic service unavailable. Root cause traced to `mcias/ingestion/api.py`: upload requires `MCIAS_STORAGE_KEY` and `MCIAS_STORAGE_DIR` or raises HTTP 503 (`encrypted storage unavailable`); strict acceptance workflow did not define either. This is the missing test-only service dependency, not proof of a production ingestion defect.

Smallest intervention: configure disposable synthetic AES key and local /tmp storage directory in contracts-only workflow. No modified authentication, data model, G2 extractor, G3/G5 rules, or financial authorization. These are disposable development-only values, never suitable for production. The strict browser test remains fail-closed; G2 source upload and any later extraction/preview failures must be recorded separately. Run evidence/artifacts and post-fix status must be inspected before any PASS claim.

DG-001 checkpoint: PR remains draft; do not merge or deploy or extend to other sections.
