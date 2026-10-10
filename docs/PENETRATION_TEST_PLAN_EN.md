# Independent penetration test plan

Document ID: `MCIAS-SEC-001` · Version: 1.0 · Status: Draft for review · Language: English

[النسخة العربية](PENETRATION_TEST_PLAN.md) · [Package index](ACCEPTANCE_PACK_INDEX_EN.md)

## Status and authorization

`NOT_EXECUTED` — this is a plan, not a security result or certificate. Active testing requires institutional signature on the [scope](PENETRATION_TEST_SCOPE_EN.md), independent tester identity, exact targets, test window and rules of engagement. This assignment does not execute attacks against external systems.

## Execution and responsibilities

1. The system owner freezes the SHA, versions, architecture and targets; the data owner authorizes synthetic data initially.
2. An independent team reviews code, configuration, permission mappings and CI evidence without treating these as final security assurance.
3. The operator provisions limited test accounts and two synthetic institutions with documented expected permissions. Signing and decryption keys are not given to the tester.
4. Bounded testing follows PT-01 through PT-15; errors and load are monitored without logging medical fields or session tokens.
5. Stop immediately on scope violation, real-data exposure or record-integrity loss. Preserve sanitized evidence and notify the incident contact named in the authorization.
6. Report findings independently, fix on a new SHA, and independently retest. Operational acceptance needs institutional signature; a successful assessment cannot grant it automatically.

## Method and evidence

Record PT-ID, SHA, target, UTC time, test account/role without secrets, expectation, reproducible steps, outcome and sanitized evidence with SHA-256. Map findings to CWE or OWASP when applicable; do not claim unreviewed compliance or certification.

Rate severity using exploitability and privacy, institutional separation and financial integrity impact, with justification and CVSS where useful. Store evidence encrypted locally with private directories, restricted access and an institution-approved retention period. Never upload medical information or secret-bearing HAR files to GitHub or public services.

## Closure

No acceptance with unresolved critical/high findings. Lower-risk exceptions need an authorized owner, expiry, documented mitigations and retesting. Mark unavailable capabilities `BLOCKED`, not passed. Production G5 execution, automatic purge and a legal-hold registry remain unavailable until implemented and approved.

The final report records authorization/scope, methodology/limitations, all PT outcomes, defect owners/fixes, retest SHA, residual risks, tester recommendation and institutional signature. Every field currently remains `NOT_RECORDED / NOT_SIGNED`.
