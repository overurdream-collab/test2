# G2 — Ingestion | Closure record (2026-10-10)

**Status: OPEN — production OCR and scanning acceptance pending.**

## Deliverables
- ReaderAgent ingestion for CSV/XLSX/PDF, encrypted originals and SHA-256 duplicate checks.
- Source page/row provenance, Palermo-1 coverage manifests, quarantine and authorized review/reprocessing.
- Local OCR/scanned-PDF support when configured, parser timeouts, ClamAV adapter and tenant-scoped APIs.

## Tests and evidence
- T01 malformed spreadsheet, T02 duplicate/revision-related checks, T03 unreadable scans and synthetic OCR/provenance regression tests.
- Cumulative CI on G4 commit `626640c1496c3bc4c71fa8fd64dfb315d4fd7035`: https://github.com/overurdream-collab/test2/actions/runs/38010322075
- Unit 112 passed / 10 skipped; PostgreSQL integration 65 passed. Synthetic OCR tests do not establish medical-document accuracy.

## Deferred
- Real-world Arabic/English OCR accuracy calibration and representative approved golden dataset.
- Fully hardened parser sandbox, operational scanning/signature management and production-scale ingestion benchmarks.

## Waiting on
- Installed and verified local ClamAV/Tesseract/language packs, real labeled documents, agreed thresholds and coverage reconciliation.
- G1 signed acceptance, G2 operational demonstration and authorized human signoff.
