"""CAI-01 read-only G2 -> G4 source-scope and row-coverage preflight.

Not an importer, audit engine, or automatic financial approval. In particular,
worksheet identity must be attested explicitly; sheet order is not inferred.
"""
from collections import defaultdict
from mcias.claim_normalization import ClaimValidationError, normalize


def inspect_extracted_records(records, *, claim_sheet_indices=None, expected_records=None):
    """Classify source rows without persisting, editing or financially auditing them.

    ``records`` are G2 ExtractedSourceRecord objects (id, locator, values).
    For XLSX, a caller must explicitly select claim sheet indexes from the
    original source. This is a diagnostic, not proof of who approved selection.
    An independent trusted approval mechanism is still required before use.
    """
    if expected_records is not None and (type(expected_records) is not int or expected_records < 0):
        raise ValueError("invalid expected_records")
    if claim_sheet_indices is not None:
        if not isinstance(claim_sheet_indices, (set, frozenset, tuple, list)):
            raise ValueError("claim_sheet_indices must be explicit integer indexes")
        if not claim_sheet_indices or any(type(i) is not int or i < 1 for i in claim_sheet_indices):
            raise ValueError("claim_sheet_indices must contain positive integer indexes")
        if len(set(claim_sheet_indices)) != len(claim_sheet_indices):
            raise ValueError("duplicate claim_sheet_indices")
        claim_sheet_indices = frozenset(claim_sheet_indices)

    entries = list(records)
    codes = set()
    observed_ids, observed_locators, observed_sheets = set(), set(), set()
    counts = dict(source=len(entries), included=0, excluded=0, unscoped=0, invalid=0, ready=0)
    by_sheet = defaultdict(lambda: dict(included=0, excluded=0, unscoped=0, invalid=0, ready=0))
    outcomes, candidates = [], defaultdict(list)
    kinds = set()
    for record in entries:
        identity = getattr(record, "id", None)
        locator = getattr(record, "locator", None)
        if not isinstance(identity, str) or not identity or not isinstance(locator, dict):
            codes.add("INVALID_SOURCE_ID_OR_LOCATOR")
            counts["invalid"] += 1
            outcomes.append({"record_id": identity if isinstance(identity, str) else None,
                             "status": "HOLD", "reason": "INVALID_SOURCE_ID_OR_LOCATOR"})
            continue
        kind, index, row = locator.get("kind"), locator.get("index"), locator.get("row")
        if kind not in ("sheet", "row") or type(index) is not int or index < 1 or type(row) is not int or row < 1:
            codes.add("INVALID_SOURCE_ID_OR_LOCATOR")
            counts["invalid"] += 1
            outcomes.append({"record_id": identity, "status": "HOLD", "reason": "INVALID_SOURCE_ID_OR_LOCATOR"})
            continue
        kinds.add(kind)
        if identity in observed_ids or (kind, index, row) in observed_locators:
            codes.add("DUPLICATE_SOURCE_ID_OR_LOCATOR")
        observed_ids.add(identity)
        observed_locators.add((kind, index, row))
        if kind == "sheet":
            observed_sheets.add(index)
        sheet = str(index) if kind == "sheet" else "csv"
        if kind == "sheet" and claim_sheet_indices is None:
            status = "UNSCOPED"
        elif kind == "sheet" and index not in claim_sheet_indices:
            status = "EXCLUDED"
        else:
            status = "INCLUDED"
        if status == "UNSCOPED":
            counts["unscoped"] += 1
            by_sheet[sheet]["unscoped"] += 1
        elif status == "EXCLUDED":
            counts["excluded"] += 1
            by_sheet[sheet]["excluded"] += 1
        else:
            counts["included"] += 1
            by_sheet[sheet]["included"] += 1
            try:
                normalized = normalize(getattr(record, "values", None))
            except ClaimValidationError:
                status = "HOLD_INVALID"
                counts["invalid"] += 1
                by_sheet[sheet]["invalid"] += 1
            else:
                counts["ready"] += 1
                by_sheet[sheet]["ready"] += 1
                semantic_key = tuple(normalized[k] for k in (
                    "beneficiary_token", "provider_code", "service_code",
                    "service_date", "claimed_amount", "currency"))
                candidates[semantic_key].append(identity)
        outcomes.append({"record_id": identity, "locator": {"kind": kind, "index": index, "row": row},
                         "status": status})

    if len(kinds) > 1:
        codes.add("MIXED_SOURCE_FORMATS")
    if "sheet" in kinds:
        if claim_sheet_indices is None:
            codes.add("CLAIM_SHEET_SELECTION_REQUIRED")
        elif not claim_sheet_indices.issubset(observed_sheets):
            codes.add("UNKNOWN_CLAIM_SHEET")
    elif claim_sheet_indices is not None:
        codes.add("SHEET_SELECTION_ON_NON_XLSX_SOURCE")
    if expected_records is not None and expected_records != counts["source"]:
        codes.add("SOURCE_COUNT_MISMATCH")
    if counts["invalid"]:
        codes.add("INVALID_CLAIM_ROWS")
    if counts["included"] == 0 and not codes:
        codes.add("EMPTY_CLAIM_SCOPE")
    if counts["included"] + counts["excluded"] + counts["unscoped"] + sum(
            1 for x in outcomes if x["status"] == "HOLD") != counts["source"]:
        codes.add("SOURCE_ACCOUNTING_MISMATCH")
    duplicates = [ids for ids in candidates.values() if len(ids) > 1]
    return {
        "status": "BLOCKED" if codes else "REVIEW_REQUIRED" if duplicates else "READY_FOR_G4",
        "reason_codes": sorted(codes), "counts": counts,
        "by_sheet": dict(sorted(by_sheet.items())),
        "row_outcomes": outcomes, "possible_duplicate_record_ids": duplicates,
        "semantics": "READ_ONLY_PREFLIGHT_NOT_FINANCIAL_AUDIT",
    }
