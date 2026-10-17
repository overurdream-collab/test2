# DG-001 — PR #25 contract acceptance login fix (2026-10-18)
Base: 4af212f6dd37a0e32d80f9685a26a93608cf8f21
Failed strict workflow: https://github.com/overurdream-collab/test2/actions/runs/39076100317

Observed: Chromium waits for the Contracts tab, but the ARIA snapshot is the login page. The acceptance script executes a hard page.goto('/admin/input-register') after login. MCIAS stores its bearer session in memory only, therefore a hard navigation discards the token and returns to sign-in. The previous assertion checked only generic main h1 and did not establish successful auth.

Smallest safe fix: assert the actual POST /api/v1/auth/login returned HTTP 200 and access_token; wait for login UI to disappear; use the application's history.pushState plus popstate SPA navigation; require visible Contracts tab and capture the authenticated real Chromium screenshot. No changes to backend, auth, RBAC, financial policy, or seven other sections.

Acceptance after fix must be judged from a NEW strict Actions run and its screenshot artifact. Any following G2/add/edit failure remains a distinct BLOCKED finding; not fixed here. No merges or deployment.
