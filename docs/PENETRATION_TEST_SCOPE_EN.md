# Penetration test scope and rules of engagement

Document ID: `MCIAS-SEC-002` · Version: 1.0 · Status: Draft for review · Language: English

[النسخة العربية](PENETRATION_TEST_SCOPE.md) · [Package index](ACCEPTANCE_PACK_INDEX_EN.md)

## Mandatory authorization record

Status: `NOT_SIGNED`. Complete before execution: institution/owner, independent tester, SHA, allowed DNS/IP/ports, UTC start/end, accounts/permissions, request/concurrency ceilings, emergency contact/reporting channel, rollback/restore plan, evidence policy and institutional/tester signatures.

Only the frozen FastAPI application, both interfaces, PostgreSQL database, encrypted source storage, archive and TLS proxy explicitly listed above are in scope. Current institutional separation uses separate installations/databases/storage plus service-level organization_id checks; do not assume comprehensive RLS. The institution must identify whether Redis, S3, OCR or other integrations are actually deployed; do not assess nonexistent components.

## Test matrix

| Test | Scope | Current result |
|---|---|---|
| PT-01 | TLS certificate integrity, headers and disabled production API docs | NOT_EXECUTED |
| PT-02 | Authentication, MFA, TOTP replay and login lockout | NOT_EXECUTED |
| PT-03 | Session expiry/logout and absence of browser token persistence | NOT_EXECUTED |
| PT-04 | RBAC and cross-institution API read/write denial | NOT_EXECUTED |
| PT-05 | Medical-column permissions and report/export disclosure denial | NOT_EXECUTED |
| PT-06 | XSS, CSP and Arabic/English text injection | NOT_EXECUTED |
| PT-07 | API input validation, SQL injection and unrestricted execution denial | NOT_EXECUTED |
| PT-08 | Excel/PDF uploads, size/complexity limits, quarantine and local ClamAV | NOT_EXECUTED |
| PT-09 | Encrypted original preservation, path traversal and unauthorized download denial | NOT_EXECUTED |
| PT-10 | Authorization signatures, trust registry and request-supplied key rejection | NOT_EXECUTED |
| PT-11 | Independent G5 grants, signatures, revocation and immutable snapshots | NOT_EXECUTED |
| PT-12 | G6 historical separation of proposer/approver and event integrity | NOT_EXECUTED |
| PT-13 | Restricted PostgreSQL role, audit_log protection and backup secrets | NOT_EXECUTED |
| PT-14 | 100/user and 1000/IP quotas, 429/503 and proxy trust boundaries | NOT_EXECUTED |
| PT-15 | Encrypted archives, isolation, receipts and 10K/128MiB bounds | NOT_EXECUTED |

## Allowed and prohibited activity

After signature: sanitized configuration review, TLS/header inspection, bounded synthetic requests, permission-denial tests and recoverable test-record changes explicitly authorized by scope. Agree load ceilings in advance; quota testing does not authorize denial of service. Login/logout are exempt from general quotas, but separate login lockout must be accounted for.

Without additional specific authorization, exclude production targets, real-data reads, wider institutional network scans, social engineering, database drops/disabled triggers, key theft, financial snapshot mutation, arbitrary code/SQL execution, off-site data transfer and destructive load/fuzz testing. External activity or SSRF targets must remain within explicitly authorized laboratory destinations.

There is no production G5 execution API, comprehensive user/organization CRUD, or automatic seven-year purge; record gaps rather than inventing successful tests. AI is advisory and cannot become an automatic financial/medical decision.

Acceptance requires no open critical/high issues, documented outcomes for available scope and independent retesting. Security sign-off cannot replace policy, UAT or G1–G9 institutional acceptance.
