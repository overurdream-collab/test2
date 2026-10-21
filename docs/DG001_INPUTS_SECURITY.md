# Independent dependency remediation — INPUTS-FIRST

Baseline main b69defa2f621458ef44d790b510840307a81009a. Scope: shared dependency/security owner; latest user-approved minimal security fix, synthetic compatibility only.

Fresh failing CI: PR32 run39524458984 job118975744860 identified Pillow12.3.0 and eight CVE-2026 IDs112895,112400,112397,112896,112897,112395,112404,112899, each with13.0.0 as fix. `pip index versions Pillow` independently confirmed13.0.0 available. Project now requires Pillow>=13.0.0,<14.

`scripts/audit_dependencies.py` inventories every installed external distribution, including all transitive, tooling and external editable packages. Only this repository's local mcias source/editable metadata is excluded from the PyPI query, after verifying its local path. External mcias metadata fails closed. Exact installed versions are passed to real pip-audit with strict errors and dependency resolution disabled because the entire resolved graph is explicitly enumerated. No vulnerability IDs are ignored and no external dependencies are excluded.

Actual verification (Python3.12.14, Pillow13.0.0, pip26.2.2, pip-audit2.10.1):
- `PYTHONPATH=. /workspace/security-venv/bin/python scripts/audit_dependencies.py -f json -o /workspace/security-audit.json`:65 external packages, zero known vulnerabilities, exit0. Raw report: docs/evidence/security-pillow13-audit.json.
- `PYTHONPATH=. /workspace/security-venv/bin/python -m pytest -q tests/test_dependency_audit.py tests/test_pillow13_compatibility.py tests/test_g2_reader.py tests/test_g2_ocr_isolation.py tests/test_g7_reporting.py tests/test_audit_export.py`:34 passed in2.12s, no skips. Includes real PNG→Tesseract/image parser and scanned PDF→PyMuPDF raster→Pillow→Tesseract with physical page provenance. OCR retains confidence0.5 and no financial authority.

Intermediate failures preserved: copied initial environment pip25.0.1 had12 advisory records (one package); upgraded actual build tooling to26.2.2 and reran, none remain. Initial local metadata validation rejected duplicate source egg-info; fixed only verified source metadata handling. Initial audit cache attempted read-only home; cache now lives in temporary directory. No audit error was suppressed. CI already upgrades pip before auditing. Unit/dependency workflows install Tesseract for the genuine compatibility tests.

Main lacks the v2 developer/acceptance documents; this maintenance adds no financial/domain API or schema so no new acceptance claims in those documents. CI at published SHA remains independently required. No merge/deploy/real patient data. First remaining issue: integration branches must adopt this independent maintenance commit before their dependency CI is green; owner coordinator. No unclosed dependency advisory in the actual audited graph.
