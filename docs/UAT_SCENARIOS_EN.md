# Institutional acceptance scenarios

Document ID: `MCIAS-UAT-002` · Version: 1.0 · Status: Draft for review · Language: English

[النسخة العربية](UAT_SCENARIOS.md) · [Package index](ACCEPTANCE_PACK_INDEX_EN.md)

## Using the scenarios

Every case starts **NOT_EXECUTED**, except UAT-25 **BLOCKED** due to missing production G5 execution workflow. Preserve actual run results separately from this plan. Record samples/hashes/time/version/role/evidence/defect/reviewer in the report template. Test sources/accounts are synthetic; later real-data scope requires independent authority.

Correct denial passes security cases; `held` is not treatment rejection. Use the API where implemented, never fictitious actions on unavailable screens. Original evidence stays within the institution.

## UAT-01 — Runtime and TLS gate

- **Role/prerequisites:** Operator; isolated environment, trusted cert, restricted identity.
- **Steps:** Run deploy_check; verify health/login and production-profile docs denial.
- **Expected:** Explicit engineering outcome, no leaks, valid TLS; missing prerequisite is BLOCKED.
- **Reference:** G1/G9; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-02 — Login, MFA and replay

- **Role/prerequisites:** Admin with encrypted enrolled factor; separate reader.
- **Steps:** Try wrong password, admin without TOTP, valid TOTP, then replay it.
- **Expected:** Invalid/missing/replayed factors denied; valid accepted; no secret in browser/report.
- **Reference:** G1; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-03 — Session and logout

- **Role/prerequisites:** Signed-in user allowed to view synthetic record.
- **Steps:** Open a record, logout, retry old session, test expiry and refresh.
- **Expected:** Revoked session denied, protected DOM cleared; no token in local/session storage.
- **Reference:** G1/T15; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-04 — Institution isolation

- **Role/prerequisites:** Two synthetic scopes and defined roles; no shared real institutional data.
- **Steps:** Request B claim/document/case/report using A identity through API, not just navigation.
- **Expected:** Deny/404 by route without B values; no unsupported tenant switching.
- **Reference:** G1/T15; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-05 — Original-field permissions

- **Role/prerequisites:** Multi-column source and ingestion.read-only actor.
- **Steps:** Request raw records with no field permissions, one field grant, then all authorized column grants.
- **Expected:** Deny page if any medical_fields.<column>.read is missing; no partial leak.
- **Reference:** T20; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-06 — Valid upload and original preservation

- **Role/prerequisites:** ingestion.upload actor, synthetic CSV/XLSX, private storage.
- **Steps:** Upload; reconcile SHA-256/rows/locators and original bytes via authorized local decrypt.
- **Expected:** Encrypted original retained, complete trace; no invented original-download URL.
- **Reference:** G2/T18; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-07 — Duplicate source and revision

- **Role/prerequisites:** Previous source and same roles.
- **Steps:** Upload identical then known revised input; inspect jobs/batches.
- **Expected:** Recognized duplicate or separate revision per implementation; no financial duplication.
- **Reference:** T02; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-08 — Quarantine, OCR and completeness

- **Role/prerequisites:** Malformed Excel and labeled unreadable scanned synthetic PDF.
- **Steps:** Upload; inspect quarantine reason/row-page locator and extraction-vs-manifest coverage.
- **Expected:** Preserved original, unsafe import blocked; OCR needs approved labeled samples/thresholds, not assumed accuracy.
- **Reference:** T01/T03; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-09 — Contract/enrollment periods

- **Role/prerequisites:** Reference writer/approver, independent reviewer; synthetic contracts/enrollments.
- **Steps:** Test overlapping approved contracts, end-date boundary and overlapping enrollments.
- **Expected:** Overlap denied, [from, until) boundaries respected; no arbitrary version selection.
- **Reference:** T04; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-10 — Retroactive impact and approval

- **Role/prerequisites:** Prior contract/claims and independent permissions.
- **Steps:** Draft a retroactive change, inspect impact/review; attempt self-approval.
- **Expected:** Documented impact/review, old version preserved; no authority bypass.
- **Reference:** T05/T07; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-11 — Import and resume

- **Role/prerequisites:** claims.import; mixed-validity batch from traced source.
- **Steps:** Preview/import; resume after synthetic interruption then repeat.
- **Expected:** Valid rows without duplication, line errors explained, counts reconcile to source.
- **Reference:** T09/T16; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-12 — Attachment tenant boundary

- **Role/prerequisites:** A claim/evidence and B evidence.
- **Steps:** Link A evidence; try B or quarantined evidence.
- **Expected:** Source/hash link preserved, invalid attachment denied; original unchanged.
- **Reference:** G4/T18; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-13 — Combined calculation evidence

- **Role/prerequisites:** Signed financial example once supplied; engineering-only fixture for now.
- **Steps:** Review stages/eight categories/Palermo-2; compare independent calculations and policy versions.
- **Expected:** Balanced arithmetic, no double deduction; fixture is not production G5 execution. Production acceptance remains BLOCKED.
- **Reference:** T08/T09; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-14 — Policy signature and revocation

- **Role/prerequisites:** Authorized policy approver/reviewer, institution-held keys.
- **Steps:** Try wrong signature/same reviewer, then revoke a grant and inspect policy state.
- **Expected:** Wrong grant denied, revoked grant cannot authorize later audit; no browser key.
- **Reference:** T06/T07; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-15 — Historical separation of duties

- **Role/prerequisites:** Case, proposer and independent reviewer.
- **Steps:** Propose, attempt self approve/reject, insert another reviewer hold, retry.
- **Expected:** All historical self approve/reject denied; event versions ordered.
- **Reference:** T11; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-16 — Objection and re-audit

- **Role/prerequisites:** Case, existing and new valid evidence.
- **Steps:** Object without then with evidence, request re-audit, try linking foreign snapshot.
- **Expected:** Missing evidence denied, valid objection traced; originals/old snapshot stable; no invented execution API.
- **Reference:** T10/T11; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-17 — Partial approval

- **Role/prerequisites:** Batch with legitimately fixture-produced held/approved rows.
- **Steps:** Create frozen report; compare payable/held count with snapshots.
- **Expected:** Held rows excluded from approved payable; claimed/per-currency values separate.
- **Reference:** T12; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-18 — Frozen reports and exports

- **Role/prerequisites:** Scoped report read/details/export permissions.
- **Steps:** Compare old report after review event; authorized export, then export without original-field grants.
- **Expected:** Old report stable, source columns preserved, unauthorized sensitive export denied.
- **Reference:** T13/T18/T20; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-19 — Advisory intelligence and tasks

- **Role/prerequisites:** Intelligence permissions, whitelisted tasks and synthetic grouped data.
- **Steps:** Run summary/signals/simulation, activate untested task, review a signal.
- **Expected:** Untested task denied; source/denominator/version visible; advisory, not fraud or binding decision.
- **Reference:** T14/T19; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-20 — UI and accessibility

- **Role/prerequisites:** Authorized roles, mobile/tablet/desktop, keyboard and screen reader.
- **Steps:** Switch ar/en/themes; test drawer/dialog/tab/focus/tables and loading/empty/error/403 states.
- **Expected:** Correct RTL/LTR, no global overflow, names/focus; automated axe plus human validation.
- **Reference:** G7/G9; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-21 — Rate limits and audit evidence

- **Role/prerequisites:** Synthetic environment, UTC windows and isolated users.
- **Steps:** Exceed 100/user and 1000/IP; test invalid session and counter-storage failure.
- **Expected:** 429/Retry-After, atomic counts, no header spoof bypass, bounded logs; storage failure 503.
- **Reference:** G1/G9; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-22 — Archival and retention

- **Role/prerequisites:** Retention permissions, completed nonempty synthetic month and local worker.
- **Steps:** Request month, run worker, verify ciphertext/hash/readback, tenant counts and exclusions.
- **Expected:** Isolated/encrypted/verified, no deletion, documented null-actor exclusion; seven years unsigned/purge disabled.
- **Reference:** G1/G9; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-23 — Backup, restore and rollback

- **Role/prerequisites:** Fresh restore DB, DB/source backup, independent key custody.
- **Steps:** Restore, verify hashes/rows/snapshots/access/app version; measure time/data loss.
- **Expected:** Restored data/originals match; RPO/RTO assessed against signed targets; no blind append-only downgrade.
- **Reference:** T17; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-24 — Unavailable features and download boundaries

- **Role/prerequisites:** Reader, source store and frontend asset allowlist.
- **Steps:** Try recovery/unready analytics/immutable editor and file path outside asset allowlist.
- **Expected:** Intentional unavailable state, no fake action; keys/originals denied; no unauthorized medical download.
- **Reference:** T15/T20; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** NOT_EXECUTED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.

## UAT-25 — Production financial execution

- **Role/prerequisites:** Signed financial decisions/authority and approved backend execution workflow.
- **Steps:** Verify an approved governed production workflow before real audit; synthetic seam is not a substitute.
- **Expected:** Currently BLOCKED: no production G5 execution API. Decision/scope/implementation/testing required before this case can pass.
- **Reference:** G5/G9; [acceptance contract](ACCEPTANCE_CONTRACT.md) and FRONTEND_ROUTE_API_MATRIX.
- **Initial status:** BLOCKED.
- **Execution evidence/tester/reviewer/defect:** NOT_RECORDED.
