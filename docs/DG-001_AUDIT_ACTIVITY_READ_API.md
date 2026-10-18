# DG-001 — First implemented slice: tenant-bounded audit history API

Base: 808a70806e6c5931b4dd5f7110e4c4d1a0a6b63e. The overall approved MCIAS unified-input specification is much broader; this commit does **not** certify full activity-log coverage or any new beneficiary-family/contract-clause lifecycle.

Implemented `GET /api/v1/workspace/activity?limit=&offset=&action=` using the pre-existing immutable `audit_log` table, existing session authentication, tenant boundary and role checks. Authorized role must have both `reference.read` and `super_admin`; the latter is an interim restrictive gate until the detailed audit RBAC matrix is agreed. Results join actor user to the tenant, exclude unknown/null actors, and intentionally omit legacy JSON `details` to avoid exposing sensitive strings. Read denial events are written for non-super-administrators.

Strict Chromium+FastAPI+PostgreSQL acceptance extends the existing Import/Add/Edit workflow, writes a synthetic foreign-organization audit event carrying a trap secret, then fetches real API events: checks revision event present, cross-tenant event absent, details absent and trap secret not returned. No real patient data. PASS only if exact-SHA GitHub Actions proves it.

**Unimplemented future gates:** recording **every** relevant read/denial/service event, comprehensive actor correlation/outbox, UI audit explorer/export, family identity/history, dynamic input schema management, contract-clause lifecycle, hierarchical permission delegation. Do not call this complete.
