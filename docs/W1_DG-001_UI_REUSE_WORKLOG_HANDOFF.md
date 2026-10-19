# DG-001 — W1 Windows UI reuse pilot — 2026-10-20

Status: ISOLATED / PARTIAL / NOT ACCEPTED. No production deployment or merge.

## Source and baseline
- main: b69defa2f621458ef44d790b510840307a81009a
- Windows source: 50ffd4bfd58661137cf079f99058159eb831e588 (PR #17)
- Pilot branch: feat/mcias-w1-windows-ui-reuse-pilot, created from main.
- Windows 11 Docker execution was confirmed by the owner and is not being repeated.

## Verified UI inventory
- Shared with main: mcias/web_workspace/app.js, views.js, workspace.css, routes.json. Do not replace wholesale.
- Windows-only: institution.js (175 lines), feature_navigation.js (65 lines). Both reference Windows-only API/feature contracts.
- Windows source includes advanced RBAC, Ed25519 approvals, registry service and migrations; explicitly excluded.
- Four W1 targets: sidebar/navigation, institution overview, institution users UI, shared UI primitives.

## Compatibility gate / findings
- The institution.js source depends on institution overview/users APIs and feature-based grants absent from main; direct copying would produce broken UI and could weaken permission semantics.
- Existing main shared UI components should remain authoritative. Do not create a second component library.
- The source route inventory is 97 routes, versus 59 on main. Route availability metadata is not proof of backend support.
- Admin grant and role changes must remain exclusively under Super Admin authority. UI visibility is never server authorization.
- Do not copy any backend, RBAC provisioning, Ed25519, registry, audit middleware, migrations, OCR or agents.

## Pilot verification state
- Historical Windows CI at SHA 50ffd4b: G1-G7, G8, G9, Enterprise, Windows launcher and Docker succeeded; they do not validate W1.
- W1 browser/permissions/tenant isolation tests: NOT RUN.
- W1 adapted UI components: NOT YET IMPLEMENTED.
- No new migration, production database, patient data or deployment used.

## HANDOFF
Implement a narrow, API-safe, main-native UI adapter. Start with route visibility using existing main permission contracts, then read-only institution dashboard, then users read-only UI. Mark unsupported actions unavailable rather than mock-authorized. Keep existing app.js/views.js/workspace.css authoritative and preserve AR/EN, RTL/LTR, light/dark and responsive layouts. Add focused Node tests and browser tests against synthetic data. Only create a Draft PR after tested UI code is available.

## Decision
W1 pilot is NOT COMPLETE. No integration or production acceptance authorized.
