# DG-001 — Contracts G2 manifest acceptance probe (2026-10-18)
Base: f6e2320d79527eeb41faa64370470f1b3930e7b5. Run that failed due to locale-dependent `document` assertion: https://github.com/overurdream-collab/test2/actions/runs/39077159536.

Changed ONLY the contracts-only strict Playwright acceptance test. It now observes the real authenticated POST /api/v1/ingestion/uploads response and requires HTTP 200, a source ID and status extracted, rather than looking for English display text. Then it clicks the existing Arabic G2 source-manifest inspection button, captures the actual GET /api/v1/ingestion/documents/{id}/manifest response, and saves actual Chromium screenshots of upload and opened manifest. It separately requires an editable, source-linked contract-fields preview before any import PASS; absence explicitly marks BLOCKED and fails CI. No new extraction features, login, storage, G3/G5 policy, add/edit functionality or other sections changed.

Expected evidence: .e2e-output/contracts-acceptance/03-upload-result.png, 04-g2-source-manifest.png, results.json. Only a new Actions run proves behavior. No main merge/deployment. Next work only after verifying this strict failure.
