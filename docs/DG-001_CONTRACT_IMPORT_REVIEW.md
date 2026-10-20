# DG-001 — Synthetic contract G2 correction/confirmation gate (2026-10-18)
Parent branch SHA: 86da87739b0ec09952bcd58d82d93783d10ee265. PR #25. Only import of synthetic PDF contract is in scope.

## Baseline reuse and controls
- Reuse unchanged G2 ingestion original storage, isolated PDF parser and persisted ExtractedSourceRecord page text/locators. Do not merge PR #23; its anchored candidate validation is informative but real-model metrics remain failed. No new generic extraction service or G3/G5 policy change.
- Add a *bounded* synthetic-English contract layout adapter in existing input-clause API. It recognizes exactly one source-backed `Service CODE Price NNN USD effective YYYY-MM-DD` quote from an extracted G2 page; unrecognized/ambiguous layouts fail closed (HTTP 409). This is not an AI contract extraction solution and is unsuitable for real contracts.
- Require tenant-bound reference.write and medical_fields.text.read, G2 extracted and complete status. Reader without reference.write cannot view/confirm.
- Editable amount remains separate from original quoted text, original numeric token, G2 document ID and page locator. Human checkbox is required in UI; server also requires human_confirmed, verifies source record and service identity, and calls the EXISTING immutable draft create workflow and audit logging. No automatic approval or financial activation.
- Strict browser acceptance checks preview does not persist before confirmation, an actual correction 125.00→126.00, reader confirmation denied, and PostgreSQL readback of original/corrected values and G2 locator.
- Does not test manual Add or Edit; those remain BLOCKED. No production merge, deploy or paid services.

## Strict limitations
This adapter only supports the pinned synthetic one-line PDF layout. Multilingual, scanned PDFs, ambiguous multi-clause contracts and genuinely reliable semantic extraction remain BLOCKED. The check must actually run on GitHub Actions before claiming PASS; screenshots and JSON in `.e2e-output/contracts-acceptance` are evidence only if produced by CI.
