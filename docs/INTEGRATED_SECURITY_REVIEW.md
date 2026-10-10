# Integrated candidate security review

Engineering review only, not penetration certification or gate acceptance.
The candidate combines enterprise PR #11 (f026862) and G9 PR #10
(c7a6eedef47887a9fa1a25b32a4a42ff15bf806a) without merging protected branches.

## Findings corrected

| Finding | Previous trigger / impact | Corrected behavior and evidence |
|---|---|---|
| S01 — raw source field disclosure | A user with `ingestion.read` could retrieve arbitrary extracted source columns, including diagnosis, through `/jobs/{id}/records`. | Each field in the returned page requires explicit `medical_fields.<field>.read`, in addition to tenant and ingestion guards. Missing/unregistered permissions deny the entire response. Test covers denial, explicit grant and foreign tenant. No implicit permission grants or schema migration. |
| S02 — rejection separation of duties | `reject` used the approval permission but lacked the independent-actor checks applied to `approve`. | Both final decisions reject the case opener and the latest actor and require a preceding proposal/hold. Negative API/unit coverage confirms no new decision event is recorded. |
| S03 — proposer conflict survives hold | A proposer other than the case opener could decide after a third actor inserted a hold, because only the latest actor was checked. | Both approve/reject check all recorded proposal actors. Real database/API tests verify an intervening hold cannot erase the conflict. |
| S04 — Compose healthcheck interpolation | Host Compose could substitute PostgreSQL variables before the container loads its private env file. | `$$POSTGRES_USER`/`$$POSTGRES_DB` defer expansion to the container. Configuration check runs with no host credentials. |
| S05 — deployment build context | Frontend test caches/node_modules could enter the Docker context after introducing the new UI. | `.dockerignore` now excludes those generated directories. Runtime includes only installed application/package assets. |
| S06 — readiness wording | UI/matrix incorrectly described existing quarantine review/reprocessing endpoints as absent. | They now explicitly identify the backend endpoints as existing but not integrated in the monitoring screen. No capability is falsely marked operational. |

## Controls inspected and exercised

- Existing server RBAC/tenant guards, bounded read-model projections, field-minimal
  metadata, same-origin requests, memory-only bearer sessions and expiry clearing.
- No browser financial calculations, arbitrary code/SQL, policy-signing keys or
  automatic AI decisions. CSP remains strict after merging G9 headers.
- G9 production OpenAPI/docs disabled; deployment remains localhost-only with
  private PostgreSQL and non-root API. Private files excluded from source/builds.
- Actual synthetic MFA login, encrypted-original preservation, malformed-file
  quarantine, denied raw source reads/exports, tenant denial, decision duty
  separation, frozen-report immutability and consequential backend audit events.
- G9 archive tampering/path traversal, receipt/signature checks, least-privilege
  database negative tests and full restore drill remain in the combined suite.

## Remaining limits

The record-level field checks use exact source column names, just as original
report export does. Institutional field mappings and role grants must be reviewed;
unknown column names fail closed. Do not grant every field to a general ingestion
reader. Clinical source references can themselves be identifying; their institutional
classification remains a policy prerequisite.

This review does not prove target-host TLS trust, network isolation, antivirus
availability, least-privilege runtime grants, key custody/rotation, production
workload capacity or penetration resistance. G9 preflight and the acceptance
contract remain applicable. The Compose harness lacks a provisioned loopback
ClamAV service; production uploads fail closed until an approved local scanner
configuration is supplied. Application HTTP audit execution remains unavailable.

All G0–G9 gates remain OPEN/BLOCKED pending their documented human approvals.
