# G2 — ReaderAgent / Ingestion implementation status

Executable G2 foundation; not gate acceptance.

## Implemented
- Encrypted original preservation via G1 AES-256-GCM store.
- SHA-256 fingerprint and tenant-scoped duplicate detection.
- File extension and magic checks; XLSX archive limits and macro/external-link rejection.
- CSV/XLSX row extraction, PDF page extraction, page/row provenance.
- Quarantine of scanned PDFs and images pending local OCR.
- PostgreSQL document/job/record/quarantine models and Alembic 0006.
- Palermo-1 coverage manifest and review-required state.
- Authenticated ingestion upload and tenant-scoped read endpoints.
- Synthetic malformed XLSX, duplicate, tenant, scanned PDF and provenance tests.

## Not yet accepted
- Structural file scanning is not an antivirus; on-prem antivirus required.
- Untrusted PDF parsing needs an isolated resource-limited worker.
- Offline OCR and measured labeled accuracy are not implemented; scanned content remains quarantined.
- PDF text is not structured claims data; normalization and confidence calibration remain.
- Revision linkage, resumable jobs, full completeness accounting, manual quarantine release, approved golden dataset and production-scale tests remain.
- G1 acceptance and operational environment checks remain separate.

## Reproducible checks
python -m pip install -e '.[test]'
python -m compileall -q mcias tests
python -m pytest -q
alembic upgrade head

G2 remains OPEN until all mandatory T01–T03, full coverage and OCR accuracy tests and G1 regression pass on the same commit with acceptance evidence.
## Additional implemented hardening
- Streaming upload size checks, including requests without a Content-Length header.
- ZIP archive duplicate/path/compression-bomb detection.
- CSV/XLSX limits and Excel formula quarantine.
- Optional Tesseract subprocess OCR for locally provisioned images; default-deny if absent.
- Spawned parser worker with timeout and best-effort OS resource limits (Linux). This is process isolation, not a hardened OS sandbox.
- OCR golden-set character-error measurement and regression tests. These synthetic metrics do not establish real medical-document OCR accuracy.
- Tenant-scoped paginated record/provenance endpoint.

## Operational acceptance still required
- Real labeled Arabic/English medical-document OCR dataset and agreed minimum accuracy thresholds.
- Locally installed and secured Tesseract, Arabic/English language packs, and PDF rasterization for scanned PDF pages.
- Mandatory antivirus or scanning service with fail-closed results before parser dispatch.
- Hardened container/OS sandbox, not merely subprocess isolation.
- Quarantine resolution with authorized reviewer, resumable ingestion, revision tracking and production-scale load tests.
- Actual on-prem restore and G1/G2 acceptance evidence.
