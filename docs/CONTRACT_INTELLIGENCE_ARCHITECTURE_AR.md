# Contract Intelligence — المخطط التقني والحدود

**الحالة:** DESIGN ONLY بعد بحث R0 بتاريخ 2026-10-17؛ لا تعتبر هذا وصفًا لكود عامل.
## المسار
G2 POST upload → IngestionDocument (org / SHA256) → IngestionJob + ExtractedSourceRecord (page / sheet row) → Palermo-1 completeness → AI inference on extracted, bounded/isolated source blocks (untrusted data) → deterministic anchor matching against exact source text and typed validation → ContractClauseProposal (draft-only) → separate reviewer/UI → ReferencePoint.create_draft existing workflow → human approval with institution-bound signature [MISSING] → optional future Typed Rule Compiler read-only diagnostic → G3/G5 hold on conflict. G6/G7/Palermo-2 unchanged.

## reuse-first boundaries
- Reuse models_ingestion, ReferencePoint/Closure, source SHA, organization_id, EncryptedStore, quarantine and ingestion API.
- Do NOT duplicate file import, original storage or audit engine. Never generate executable SQL/Python. AI must never output authoritative amounts or trigger POST /approve.
- A proposal must retain a job/document/org link, original quote, exact locator, extracted typed value, candidate rule type, reference version, model identifier+revision, request digest, response hash, validation status/conflict diagnostics and timestamps.
- A deterministic validator must require the original quote to match an extracted record exactly (normalized whitespace only for matching, never alter stored quote); must enforce exact page/row locator and typed Decimal; currency uppercase; no auto-inferred dates. OCR price/percent remains manual review unless independently verified.
- Do not coerce a missing effective_from into today's date. Existing ReferencePoint requires start date; proposals may remain unpromoted until reviewer supplies it. A proposal must never approve itself.
- Non-textual exclusions/country/membership/clinical judgment → INDETERMINATE/HUMAN_REVIEW. Duplicate same SHA within org refers to prior source only.
- For after-handoff code, prefer explicit datastore on existing DB via additive alembic 0020+ only if necessary, with append-only decisions and tenant-indexed queries; validate RBAC and numeric constraints. No third-party hosted inference, no model download from user data or remote endpoint.
- Type compiler may return DIAGNOSTIC PASS/INDETERMINATE/CONFLICT only, never payment instruction; G3/G5 remain authoritative. Reuse reference_rule_bridge when comparing approved clauses; use service_date half-open intervals.
- Security: SSRF prevention on localhost inference URL (allowlist fixed operator config); no external proxy, no PHI logs; prompt data fenced as UNTRUSTED; parse JSON strict schema, size/time limits; fail closed; limit files/pages, authorization, row-level tenant filter.
## Test inventory
Data: Arabic 10p, English, bilingual, native+scan PDF, XLSX three providers, amendment, stale billing, no date, OCR error, prompt injection, duplicate, model timeout, auth, no activation, PG concurrency/immutability, browser a11y, precision/recall. **Not executed as a suite yet**.

## C1 code reality
mcias/contract_intelligence.py is pure validation + local HTTP transport only, not a backend route. It uses record_id/locator/fields supplied by G2 after future authorization; output status forced DRAFT_ONLY. It does not persist candidate data nor call G3/G5. NOTE: CSV row locator is not currently included in accepted type set except row; read API adapter must preserve G2 kind exactly.

## C2 live boundaries
HTTP preview at /api/v1/contract-intelligence/documents/{document_id}/preview only. source selection is tenant- and permission-scoped; G2 field-level control is reused. model is loopback-only, optional runtime required. Preview results in memory and response with exact G2 locator; bad OCR forces human review. No background job or persistent proposal; human must independently create ReferencePoint via separate existing UI, institution-level signed approval still missing. No G3/G5 changes.
