# G0 Architecture Decision Register

Statuses: APPROVED, PROPOSED, OPEN, BLOCKED. Record owner, rationale, alternatives, approval and evidence for each decision.

| ID | Decision | Status |
|---|---|---|
| ADR-001 | Separate on-premises PostgreSQL per client | APPROVED baseline |
| ADR-002 | FastAPI, SQLAlchemy and Alembic | PROPOSED |
| ADR-003 | React and TypeScript UI | PROPOSED |
| ADR-004 | Authentication, MFA and sessions | OPEN |
| ADR-005 | Local file encryption and key custody | OPEN |
| ADR-006 | Encrypted backups and recovery | OPEN |
| ADR-007 | CI and reproducible test environment | OPEN |
| ADR-008 | Local OCR and AI sandbox | OPEN |
| ADR-009 | Contract precedence and temporal rules | BLOCKED pending written policy |
| ADR-010 | Financial calculation basis and rounding | BLOCKED pending policy |
| ADR-011 | Retention, target load and medical-field access | BLOCKED pending policy |

An ADR is not evidence of passing software tests. See docs/ACCEPTANCE_CONTRACT.md and GATE_STATUS.md.

## Financial policy decisions and current implementation

The 13 FIN-ADR proposals in [POLICY_PACK](policies/POLICY_PACK_EN.md) are separate from this architecture index. Historical framework proposals are not implementation evidence: the current enterprise workspace uses vanilla JavaScript ES modules served by FastAPI. Decisions remain subject to institutional approval.
