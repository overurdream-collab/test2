# Contract Intelligence — سجل القرارات

## CID-001 — 2026-10-17 — RESEARCHED / pending real benchmark
Decision: Keep existing MCIAS G2/pypdf/openpyxl/Tesseract as default; don't install Docling/MinerU/Marker just because popular. Rationale: source encryption, tenant isolation, quarantine, typed record locators already exist; replacing breaks proven invariants. Alternatives evaluated: Docling MIT, MinerU custom license, PaddleOCR Apache, Unstructured Apache, Marker code Apache+weights restricted, OCRmyPDF MPL. Risks: loss of table layout and Arabic OCR unreliability. Next: native vs Docling/Paddle benchmark with gold synthetic corpus.
## CID-002 — 2026-10-17 — CANDIDATE / NOT VERIFIED
Decision: Qwen3-4B-Instruct-2507 Apache-2.0 first model *candidate* for bounded structured JSON on local inference, with Qwen3-VL only for image complexity. No inference has run. No external PHI; a local model runtime must be configured and tested, do not assume Gateway exists.
## CID-003 — 2026-10-17 — BINDING SAFETY
AI gives citations/typed proposals only, never active financial instructions. Evidence resolver rechecks exact quote against original extracted record, page/row, tenant; uncertain/missing dates or mismatched OCR numeric values demand human review. No eval/exec/LLM SQL. Typed compiler diagnostic only before institutional signature; G3/G5 unchanged. See DG-001 / PR #22.
## CID-004 — 2026-10-17 — DATA CONTRACT
Use existing ReferencePoint/Closure after human promotion; before that store draft-only candidate records scoped org/document/job. If additive table necessary use Alembic new revision (0020+) and do not alter 0019. No deletions of historical source, point or closure. All prices isolated by provider/service/currency/effective date.


## CID-005 — C8 constrained pretrained CPU evaluation (PENDING_CI)
Decision: Test official `Qwen/Qwen3-0.6B` Apache-2.0 revision `c1899de289a04d12100db370d81485cdf75e47ca` on 4 synthetic Arabic/English/mixed/injection text cases in free standard public GitHub Actions, local loopback only. This is not final model selection: 0.6B is a resource-compatible feasibility baseline compared with earlier Qwen3-4B candidate, not proven accurate. Do not export real contracts. Record actual model output hashes and TP/FP/FN via `scripts/contract_ai_benchmark.py`, never fabricate success. If dependency downloads fail, status BLOCKED and investigate smaller legally licensed model or a private approved runner; no money spent. Need larger 20+ synthetic fixtures and OCR gold for final selection.
