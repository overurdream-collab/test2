# User acceptance checklist

Document ID: `MCIAS-UAT-003` · Version: 1.0 · Status: Draft for review · Language: English

[النسخة العربية](UAT_CHECKLIST.md) · [Package index](ACCEPTANCE_PACK_INDEX_EN.md)

## Before execution

- [ ] Define acceptance type/scope/full SHA/package hash
- [ ] Identify authority, independent finance reviewer and security/privacy owners
- [ ] Authorize data/sources and separate test databases
- [ ] Distinct roles/access matrix/MFA without recorded secrets
- [ ] Record external results, policy version and approved reference calculations
- [ ] Rehearse backup/restore/rollback, no blind append-only downgrade

## Cases and evidence

- [ ] UAT-01: Runtime and TLS gate — record result/evidence/reviewer; not externally executed.
- [ ] UAT-02: Login, MFA and replay — record result/evidence/reviewer; not externally executed.
- [ ] UAT-03: Session and logout — record result/evidence/reviewer; not externally executed.
- [ ] UAT-04: Institution isolation — record result/evidence/reviewer; not externally executed.
- [ ] UAT-05: Original-field permissions — record result/evidence/reviewer; not externally executed.
- [ ] UAT-06: Valid upload and original preservation — record result/evidence/reviewer; not externally executed.
- [ ] UAT-07: Duplicate source and revision — record result/evidence/reviewer; not externally executed.
- [ ] UAT-08: Quarantine, OCR and completeness — record result/evidence/reviewer; not externally executed.
- [ ] UAT-09: Contract/enrollment periods — record result/evidence/reviewer; not externally executed.
- [ ] UAT-10: Retroactive impact and approval — record result/evidence/reviewer; not externally executed.
- [ ] UAT-11: Import and resume — record result/evidence/reviewer; not externally executed.
- [ ] UAT-12: Attachment tenant boundary — record result/evidence/reviewer; not externally executed.
- [ ] UAT-13: Combined calculation evidence — record result/evidence/reviewer; not externally executed.
- [ ] UAT-14: Policy signature and revocation — record result/evidence/reviewer; not externally executed.
- [ ] UAT-15: Historical separation of duties — record result/evidence/reviewer; not externally executed.
- [ ] UAT-16: Objection and re-audit — record result/evidence/reviewer; not externally executed.
- [ ] UAT-17: Partial approval — record result/evidence/reviewer; not externally executed.
- [ ] UAT-18: Frozen reports and exports — record result/evidence/reviewer; not externally executed.
- [ ] UAT-19: Advisory intelligence and tasks — record result/evidence/reviewer; not externally executed.
- [ ] UAT-20: UI and accessibility — record result/evidence/reviewer; not externally executed.
- [ ] UAT-21: Rate limits and audit evidence — record result/evidence/reviewer; not externally executed.
- [ ] UAT-22: Archival and retention — record result/evidence/reviewer; not externally executed.
- [ ] UAT-23: Backup, restore and rollback — record result/evidence/reviewer; not externally executed.
- [ ] UAT-24: Unavailable features and download boundaries — record result/evidence/reviewer; not externally executed.
- [ ] UAT-25: Production financial execution — record result/evidence/reviewer; currently BLOCKED.

## Decision conditions

- [ ] Explain every FAIL/BLOCKED/NOT_EXECUTED, skip and warning without hiding them in a passing total.
- [ ] No critical unresolved defect/mandatory financial-privacy failure; retest tied to fix SHA.
- [ ] Independent penetration testing, recovery/performance and real permission evidence attached internally.
- [ ] Financial/authority/retention decisions signed or their blocked scope explicitly recorded.
- [ ] Limited engineering acceptance is not comprehensive production approval; UAT-25 stays blocked until implemented.
- [ ] Only authorized signature updates gate status after satisfying the contract.

## Authority completes disposition

Accepted scope: **NOT_RECORDED**. Accepted/blocked cases: **NOT_RECORDED**. Comments/residual impact: **NOT_REVIEWED**. Tester/reviewer names/date: **NOT_RECORDED**. Final signature: **NOT_SIGNED**. Production activation authority: **NOT_ISSUED**.

A checked box is not execution evidence. Checklist intentionally starts empty; no developer signs for the institution.
