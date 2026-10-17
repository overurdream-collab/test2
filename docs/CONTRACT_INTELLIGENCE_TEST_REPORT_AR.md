# Contract Intelligence — تقرير الاختبار الإثباتي

**الحالة: البحث R0 فقط — NOT COMPLETED.** لا تُحَوِّل نجاح pipeline native إلى ادعاء نجاح وكيل AI.
| Case | Evidence | Result |
|---|---|---|
| GitHub PR state | PR #22 open draft at b694a2a1603a9a4c6d7af26ed56035b1a28b0166؛ PR #19 open draft | VERIFIED metadata |
| Native PDF 2 pages | python /mnt/data/ci_research_tests/probe.py, ReportLab synthetic text, pypdf strict | PASS local smoke (2 anchor facts, **not** accuracy metric) |
| Synthetic English OCR image | tesseract -l eng returned CONSULT H1 5000 YER, return code 0 | PASS local smoke only |
| Synthetic workbook | artifact_tool generated XLSX for H1/H2/H3 size 3475 bytes | PASS file creation; parser NOT_RUN |
| Arabic OCR + mixed PDF, tables, six projects integration | packages/download unavailable and no canonical fixtures copied into repo | NOT_RUN |
| Qwen3 real inference | no locally installed model/runtime or approved GPU, no Hugging Face download from sandbox | NOT_RUN / BLOCKED |
| 20 acceptance scenarios + security/PG/API/browser | Contract Intelligence feature not written at R0 | NOT_RUN |
| Precision/Recall/FPR/FNR | Gold set + predictions absent | NOT_MEASURED |
| CI at research commit | must query Actions on exact HEAD after commit | PENDING_CI |

## Mandatory next reproducible steps
1. Build privacy-safe committed SYN contract fixture generator (Arabic shaped + text PDF + scanned + multilingual + XLSX); run tests on actual repo/CI.
2. Use isolated dependency profile to evaluate Docling CPU and existing pypdf; include license/model revision and page/table row offsets.
3. Launch approved *local* OpenAI-compatible Qwen runtime (Ollama/vLLM optional), record model SHA and actual response without PHI.
4. Compute TP/FP/FN per clause on frozen gold annotations; Precision=TP/(TP+FP), Recall=TP/(TP+FN), FPR on defined negatives, no estimated success percentages.
5. GitHub Actions on exact branch HEAD for G1–G9, governance, integration and browser, attach URLs/status. Independent review before merge.

## C1 evidence gate
New tests/test_contract_intelligence.py introduces synthetic tests for quote, row, source hash, typed Decimal, duplicate and conflicting clauses, missing dates, prompt injection, endpoint SSRF and model unavailable. **No PASS attributed to the repository** until GitHub Actions shows exact SHA; PENDING_CI. No extraction precision/recall available. Synthetic model ids in tests are not real inference.

## C2 proof status
Added synthetic tests/test_contract_intelligence_api.py with user permissions, cross tenant, source quarantine, missing model env, OCR uncertainty and medical field access. In test, infer_local is MOCKED and the result must never be claimed as real AI. Python/JS/PG CI of C2 exact SHA PENDING_CI. C1 confirmed Governance run 39058718203 success and MCIAS G1-G7 run 39058718217 success at 453aebde6a8d349207331bbd0bd1b96c5bc34169.

## CI failure and correction C2→C3
At SHA 1d84f576ea75c5632c8d2686c2c8d00021c75212, G1-G7 run https://github.com/overurdream-collab/test2/actions/runs/39059261540 unit job failed test_malformed_model_json_types_are_reviewed_not_executed: TypeError for list-valued provider_code. 389 passed / 20 skipped / 1 failed, postgres-integration and dependency audit successful. Governance and G9 PASS. New code type-checks provider/service and ties numeric value to the candidate quote (not page). Additional negative test for two prices on the same page. New SHA PENDING_CI.

### Source-level tests C4
- Added four synthetic file reader cases in tests/test_contract_documents.py using reportlab/Pillow/openpyxl output read through actual G2 ReaderAgent. Native PDF page and XLSX row mapping, scanned page quarantine, source prompt-as-text. This does not prove Arabic OCR, Qwen3 inference, clause precision/recall or production safety. New SHA PENDING_CI.
