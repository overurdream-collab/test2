# Enterprise frontend route-to-API coverage

Baseline: `feat/g8-intelligence` at `f5117ff4a736334288cd411faea395b3ae4d9886`.
All 59 workspace routes plus 3 authentication routes have intentional UI states.
**No G0–G9 gate is accepted.** “Integrated / partial” means the listed engineering
API is used under authorization; it does not mean the full requested module exists.

Every protected screen first obtains `/api/v1/workspace/context`. Administration
requires the `super_admin` role in the UI. Backend projection reads additionally
require tenant equality and explicit permissions. `users.read` has no default grant
and requires a Super Admin role on the server. Each existing mutation retains its
existing backend permission and institutional controls. Single-organization scope
is intentional: the acceptance contract requires separate local installations.

| Frontend route | UI / backend coverage | API contract | Read permission / limitation |
|---|---|---|---|
| `/admin/dashboard` | Integrated — partial | GET /api/v1/workspace/context | profile.read |
| `/admin/organizations` | Unavailable — planned | No operational API | Separate on-premises installation per organization. A cross-installation tenant registry and switching API are unavailable. |
| `/admin/users` | Integrated — partial | GET /api/v1/workspace/catalog/users | users.read |
| `/admin/roles` | Unavailable — planned | No operational API | Backend RBAC is enforced. Role editing and permission grant APIs are unavailable. |
| `/admin/permissions` | Integrated — partial | GET /api/v1/workspace/context | profile.read |
| `/admin/security` | Integrated — partial | POST /api/v1/auth/mfa/enroll, /confirm | profile.read |
| `/admin/audit-logs` | Unavailable — planned | No operational API | Append-only logging exists. A governed viewer and sensitive-field redaction API are unavailable. |
| `/admin/data-sources` | Integrated — partial | GET /api/v1/workspace/catalog/documents; GET /api/v1/ingestion/documents/{id}/manifest | ingestion.read |
| `/admin/ingestion` | Integrated — partial | GET /api/v1/workspace/catalog/jobs; GET /api/v1/ingestion/jobs/{id}[ /quarantine]; POST /api/v1/ingestion/uploads | ingestion.read |
| `/admin/quarantine` | Integrated — partial | GET /api/v1/workspace/catalog/jobs; GET /api/v1/ingestion/jobs/{id}/quarantine | ingestion.read |
| `/admin/reference-data` | Integrated — partial | GET /api/v1/workspace/catalog/contracts; GET /api/v1/reference/contracts/active/{provider_code}; admin: POST contracts, tariffs, CSV tariff import, categories, enrollments, authorization, precedence-review, impact-review, approve | reference.read |
| `/admin/financial-policies` | Integrated — partial | POST /api/v1/audit-policies/grants, /grants/{id}/revoke | Action-specific permission / no implicit grant |
| `/admin/policy-approvals` | Integrated — partial | POST /api/v1/audit-policies/grants, /grants/{id}/revoke | Action-specific permission / no implicit grant |
| `/admin/ai-agents` | Integrated — partial | GET/POST /api/v1/intelligence/studio/tasks; GET /studio/tasks/{id}; POST /studio/tasks/{id}/{test,activate,deactivate} | intelligence.studio.read |
| `/admin/analysis-tasks` | Integrated — partial | GET/POST /api/v1/intelligence/studio/tasks; GET /studio/tasks/{id}; POST /studio/tasks/{id}/{test,activate,deactivate} | intelligence.studio.read |
| `/admin/rules` | Integrated — partial | GET /api/v1/rules/{id}; POST /api/v1/rules/{id}/activate | rules.read |
| `/admin/indicators` | Integrated — partial | GET /api/v1/intelligence/capabilities | intelligence.read |
| `/admin/thresholds` | Integrated — partial | GET/POST /api/v1/intelligence/studio/tasks; GET /studio/tasks/{id}; POST /studio/tasks/{id}/{test,activate,deactivate} | intelligence.studio.read |
| `/admin/workflows` | Unavailable — planned | No operational API | G6 events exist; configurable stages, assignment and escalation APIs are unavailable. |
| `/admin/integrations` | Unavailable — planned | No operational API | An integration-management API is unavailable. Medical data must remain on premises. |
| `/admin/system-health` | Integrated — partial | GET /health/live, /health/ready | Action-specific permission / no implicit grant |
| `/admin/backups` | Unavailable — planned | No operational API | Local backup tooling exists. Scheduling and restore-status APIs with separated duties are unavailable. |
| `/admin/alerts` | Unavailable — planned | No operational API | Analysis signals are separate from notifications. An alert inbox and delivery API are unavailable. |
| `/admin/settings` | Integrated — partial | GET /api/v1/workspace/context (UI preferences only) | profile.read |
| `/institution/dashboard` | Integrated — partial | GET /api/v1/report-explorer/snapshots, /snapshots/{id}/entries | reports.read |
| `/institution/claims` | Integrated — partial | GET /api/v1/workspace/catalog/claims; POST /api/v1/claims/entries/{id}/attachments/{document_id} | claims.read |
| `/institution/claims/batches` | Integrated — partial | GET /api/v1/workspace/catalog/batches; GET /api/v1/claims/batches/{id}[ /entries]; POST /batches/from-document/{id}, /batches/{id}/resume | claims.read |
| `/institution/beneficiaries` | Integrated — partial | GET /api/v1/reference/eligibility/{token}?at=YYYY-MM-DD | reference.read |
| `/institution/providers` | Integrated — partial | GET /api/v1/workspace/catalog/contracts; GET /api/v1/reference/contracts/active/{provider_code}; admin: POST contracts, tariffs, CSV tariff import, categories, enrollments, authorization, precedence-review, impact-review, approve | reference.read |
| `/institution/hospitals` | Unavailable — planned | No operational API | An authoritative provider-type registry and type-specific analytics API are unavailable. |
| `/institution/laboratories` | Unavailable — planned | No operational API | Laboratory analytics require governed service and provider categorization. |
| `/institution/pharmacies` | Unavailable — planned | No operational API | A categorized pharmacy registry and dispensing analytics are unavailable. |
| `/institution/medications` | Unavailable — planned | No operational API | Medication reference data and evidence-linked expenditure analytics are unavailable. |
| `/institution/procedures` | Unavailable — planned | No operational API | Service codes exist; a procedure dictionary and clinical cost indicator API do not. |
| `/institution/utilization` | Integrated — partial | GET /api/v1/intelligence/runs, /runs/{id}; POST /runs (summary) | intelligence.read |
| `/institution/insurer-billing` | Unavailable — planned | No operational API | Insurer ledger, billing contracts and approved reconciliation rules are required. |
| `/institution/financial-audit` | Integrated — partial | GET /api/v1/workspace/catalog/audits; GET /api/v1/audits/{id} | claims.read |
| `/institution/duplicates` | Integrated — partial | GET /api/v1/audits/{id} (existing duplicate agent only) | claims.read |
| `/institution/anomalies` | Integrated — partial | GET /api/v1/intelligence/runs, /runs/{id}, /runs/{id}/review-summary; POST /runs (signals), /runs/{id}/signals/{index}/reviews | intelligence.read |
| `/institution/waste-analysis` | Unavailable — planned | No operational API | No approved policy or validated reference dataset supports classifying expenditure as unnecessary. |
| `/institution/contract-gaps` | Integrated — partial | GET /api/v1/reference/contracts/{id}/impact | reference.read |
| `/institution/cost-optimization` | Integrated — partial | GET /api/v1/intelligence/runs, /runs/{id}; POST /runs (simulation) | intelligence.read |
| `/institution/quality` | Unavailable — planned | No operational API | Quality indicators need approved definitions and evidence-backed denominators. |
| `/institution/trends` | Integrated — partial | GET /api/v1/intelligence/runs, /runs/{id}; POST /runs (summary) | intelligence.read |
| `/institution/evidence` | Integrated — partial | GET /api/v1/workspace/catalog/documents; GET /api/v1/ingestion/documents/{id}/manifest | ingestion.read |
| `/institution/reviews` | Integrated — partial | GET /api/v1/workspace/catalog/cases; GET /api/v1/governance/cases/{id}; POST /cases/from-audit/{id}, /cases/{id}/events | claims.read |
| `/institution/appeals` | Integrated — partial | GET /api/v1/workspace/catalog/cases; GET /api/v1/governance/cases/{id}; POST /cases/{id}/events (object, request_reaudit, link_reaudit) | claims.read |
| `/institution/ai-intelligence` | Integrated — partial | GET /api/v1/intelligence/runs, /runs/{id}; POST /runs (summary) | intelligence.read |
| `/institution/alerts` | Integrated — partial | GET /api/v1/intelligence/runs, /runs/{id}, /runs/{id}/review-summary; POST /runs (signals), /runs/{id}/signals/{index}/reviews | intelligence.read |
| `/institution/reports` | Integrated — partial | GET /api/v1/report-explorer/snapshots, /snapshots/{id}/entries; GET /api/v1/reports/snapshots/{id}/excel, /pdf; POST /reports/batches/{id}/snapshots, /reports/snapshots/{id}/beneficiary-statement | reports.read |
| `/institution/settings` | Integrated — partial | GET /api/v1/workspace/context (UI preferences only) | profile.read |
| `/shared/profile` | Integrated — partial | GET /api/v1/workspace/context | profile.read |
| `/shared/notifications` | Unavailable — planned | No operational API | A notification store and message delivery API are unavailable. |
| `/shared/help` | Integrated — partial | Static guidance; no records | Action-specific permission / no implicit grant |
| `/admin/organizations/[recordId]` | Unavailable — planned | No operational API | Unavailable in the current backend. |
| `/admin/users/[recordId]` | Integrated — partial | GET /api/v1/workspace/users/{id} | users.read |
| `/institution/claims/[recordId]` | Integrated — partial | GET /api/v1/workspace/claims/{id} | claims.read |
| `/institution/beneficiaries/[recordId]` | Integrated — partial | GET /api/v1/reference/eligibility/{token}?at=YYYY-MM-DD | reference.read |
| `/institution/providers/[recordId]` | Integrated — partial | GET /api/v1/reference/contracts/active/{provider_code}?at=YYYY-MM-DD | reference.read |

| Authentication route | Coverage | API |
|---|---|---|
| `/login` | Password + TOTP; memory-only bearer session | POST `/api/v1/auth/login`; GET `/api/v1/workspace/context`; POST `/api/v1/auth/logout` |
| `/mfa` | Sign-in with TOTP; enrollment lives at `/admin/security` | Same login API; POST MFA enroll/confirm from security workspace |
| `/forgot-password` | Unavailable recovery API; institution-admin guidance | None; no email/reset action is simulated |
| `/` | Redirects to institution dashboard; unauthorized browser sees sign-in | No data is embedded in HTML |

## Important partial coverage boundaries

- Dashboard: one frozen G7 report, per-currency backend totals and counts. No duplicate counting across report versions, fabricated comparisons, synchronization dates, “potential savings”, active-beneficiary totals or utilization denominator. Currency chart drill-down requests authorized report entries.
- G5: immutable read-only snapshots, all eight named agents, Decimal strings and independent verification. Absent findings/adjustments remain absent. No production execution API exists. A G5 result is separate from a G6 approved decision.
- G6: existing append-only actions, objections with verified evidence, requested/linked re-audit. Assignment, escalation, free-text medical comments, configurable stages and a full appeals lifecycle are unavailable.
- G8: summary grouping by provider/service/month, privacy suppression, review-only signals, explicitly hypothetical cost scenarios, whitelisted task versions, server-side tests and independent activation. Geographic analytics, medication categorization, generative AI/chat, arbitrary prompts/SQL/code and scheduling are unavailable. Monthly visualizations show recorded months only, not invented zero values.
- Reference: provider codes and temporal contracts, not a classified provider census. Eligibility lookup is not a beneficiary medical profile. Medical field rights remain enforced by the existing statement/export APIs.
- Documents: source hash, status, manifest and quarantine locators; original downloads lack an authorized HTTP API. Quarantine review and reprocessing endpoints exist in the backend but their actions are not integrated into this screen. Raw extracted records are not rendered; the integrated candidate additionally requires explicit permission for every source field before the existing records API returns values.
- Platform: read-only current-user identity/effective permissions and tenant-scoped user listing. Organization CRUD, user CRUD, role editing, access-log viewer, feature-entitlement editing, workflow/integration editors, backup scheduler and version-history management have no supported APIs.
- PDF/Excel exports go through the backend. Original-field export remains omitted by default; field entitlements are never bypassed. Table sorting/filtering is explicitly limited to the loaded page; pagination is server-backed. There is no universal client-side export of protected tables.
- Unsupported mutations are not given clickable fake actions. Available forms are disabled without effective permissions, and are fully disabled in synthetic preview mode. A role or permission change still needs authorization at the backend on every request.
