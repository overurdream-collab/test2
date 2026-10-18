# DG-001 — G3 contract selection refresh (2026-10-18)
Strict run https://github.com/overurdream-collab/test2/actions/runs/39136777017 confirmed Import PASS and Add PASS, then failed to find the just-added G3 contract selector. Catalog fetched before addition and was not refreshed; the contract record selected from G3 also lacked `section:"contracts"`, preventing the existing editAction scope check from admitting it.

Minimal correction: selecting the Contracts tab again in the real Chromium acceptance test refreshes the bounded, tenant-scoped G3 catalog. Selected G3 contract now explicitly carries section contracts in UI state. No backend/policy changes and no attempt to bypass RBAC. Repeat strict Chromium+PostgreSQL acceptance before claiming Edit PASS. PR draft; no merge/deploy.
