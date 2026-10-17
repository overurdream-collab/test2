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
