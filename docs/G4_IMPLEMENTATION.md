"""G4 source-linked claims: implementation and acceptance checklist.

Scope: batches, immutable claim entries, attachments and resumable ingestion.
The G2 ingestion source is authoritative; original source bytes and extracted
record locators remain linked to every G4 claim. No AI makes clinical judgments.
No deductions or financial recalculations are performed in G4.

Endpoints:
POST /api/v1/claims/batches/from-document/{document_id}
GET /api/v1/claims/batches/{batch_id}/preview
POST /api/v1/claims/batches/{batch_id}/resume
GET /api/v1/claims/batches/{batch_id}
GET /api/v1/claims/batches/{batch_id}/entries
POST /api/v1/claims/entries/{claim_id}/attachments/{document_id}

Required CSV/XLSX headers: claim_reference, beneficiary_token,
provider_code, service_code, service_date (YYYY-MM-DD),
claimed_amount (decimal, max four fractional digits), currency (ISO-like
three uppercase letters). Other source fields are preserved verbatim.
Original values cannot be edited through the G4 API. A correction must
create a new G2 source document and G4 batch.

G4 does not automatically approve eligibility, service codes or tariffs.
Those are governed by G3 references and the future deterministic G5 engine.

Review blockers: an incomplete or quarantined source cannot be staged;
invalid row values are returned with original locators and require review.
Imports resume idempotently using source record IDs and bounded chunks.
For production, test failure recovery, isolation, source integrity,
PostgreSQL constraints and performance against the institution's target load.
Gate remains OPEN pending acceptance, operational benchmarks and signoff.
