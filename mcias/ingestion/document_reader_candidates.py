"""Untrusted invoice candidates adapted from the isolated Document Reader layout pilot.

This is a bounded *candidate detector*, not a trained medical AI agent.  Its
results cannot authorize financial actions or prove a claim matches an invoice.
The original pilot lives on feat/mcias-document-reader-isolated-pilot in
scripts/document_reader_dynamic_layout_pilot.py.
"""
from __future__ import annotations

import re
import statistics

ALIASES = {
    "ID": "id", "REF": "id", "CODE": "code", "SERVICE": "code",
    "UNIT": "unit", "MEASURE": "unit", "QTY": "qty", "COUNT": "qty",
    "PRICE": "price", "RATE": "price", "TOTAL": "total", "AMOUNT": "total",
    "الرقم": "id", "الخدمة": "code", "الوحدة": "unit",
    "الكمية": "qty", "السعر": "price", "الإجمالي": "total",
}
PATTERNS = {
    "id": r"[A-Z]{2}",
    "code": r"(?:[A-Z][A-Z0-9-]+|[\u0621-\u064A]+)",
    "unit": r"(?:[A-Z]{2}|[\u0621-\u064A]+)",
    "qty": r"[1-9][0-9]*",
    "price": r"[0-9]+\.[0-9]{2}",
    "total": r"[0-9]+\.[0-9]{2}",
}


def _lines(words):
    lines = []
    for word in sorted(words, key=lambda w: (w["bbox"][1] + w["bbox"][3]) / 2):
        cy = (word["bbox"][1] + word["bbox"][3]) / 2
        near = [(abs(cy - line["mid"]), i) for i, line in enumerate(lines)
                if abs(cy - line["mid"]) < 28]
        if near:
            line = lines[min(near)[1]]
            line["words"].append(word)
            line["mid"] = statistics.median(
                (item["bbox"][1] + item["bbox"][3]) / 2 for item in line["words"]
            )
        else:
            lines.append({"mid": cy, "words": [word]})
    for line in lines:
        line["words"].sort(key=lambda w: w["bbox"][0])
    return sorted(lines, key=lambda line: line["mid"])


def _anchor(words, document_id, sha256):
    box = [min(w["bbox"][0] for w in words), min(w["bbox"][1] for w in words),
           max(w["bbox"][2] for w in words), max(w["bbox"][3] for w in words)]
    return {
        "value": " ".join(w["text"] for w in words),
        "page": 1, "bbox_pixels": box,
        "ocr_confidence_uncalibrated": min(w["confidence_uncalibrated"] for w in words),
        "source": {"document_id": document_id, "sha256": sha256,
                   "locator": "pdf:page:1:bbox:" + ",".join(map(str, box))},
        "status": "UNATTESTED_DOCUMENT_CANDIDATE",
    }


def _metadata(lines, before, document_id, sha256):
    found = {}
    issues = []
    iso = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
    labels = {
        "service_date": rf"(SERVICE_DATE|SERVICE DATE|تاريخ الخدمة)\s+({iso})",
        "document_date": rf"(DATE|INVOICE_DATE|التاريخ)\s+({iso})",
        "provider": r"(PROVIDER|PROVIDER_CODE|مقدم الخدمة)\s+([A-Za-z0-9][A-Za-z0-9_.:-]{0,79})",
    }
    for i, line in enumerate(lines[:before], 1):
        words = line["words"]
        sentence = " ".join(w["text"] for w in words)
        labelled_date = False
        for key, regex in labels.items():
            match = re.fullmatch(regex, sentence)
            if not match:
                continue
            label, value = match.groups()
            parts = [w for w in words if w["text"] == value]
            if len(parts) != 1:
                issues.append("AMBIGUOUS_METADATA_" + key)
                continue
            candidate = _anchor(parts, document_id, sha256)
            candidate.update(value=value, source_label=label, source_line=i,
                             semantic_role="provider_code" if key == "provider" else key)
            found.setdefault(key, []).append(candidate)
            labelled_date = key in {"service_date", "document_date"}
        if re.search(iso, sentence) and not labelled_date:
            issues.append("UNLABELLED_METADATA_DATE")
        for key, regex in {
            "invoice_number": r"INV-[0-9]{4}-[0-9]{3}",
            "currency": r"\b(?:USD|YER)\b",
            "stated_total": r"[0-9]+\.[0-9]{2}",
        }.items():
            if key == "stated_total" and not any(
                word in sentence.upper() for word in ("GRANDTOTAL", "المجموع")
            ):
                continue
            match = re.search(regex, sentence)
            if not match:
                continue
            parts = [w for w in words if match.group() in w["text"]]
            if parts:
                candidate = _anchor(parts, document_id, sha256)
                candidate.update(value=match.group(), source_line=i, semantic_role=key)
                found.setdefault(key, []).append(candidate)
    fields = {}
    for key, choices in found.items():
        if len(choices) != 1:
            issues.append("AMBIGUOUS_METADATA_" + key)
        elif "AMBIGUOUS_METADATA_" + key not in issues:
            fields[key] = choices[0]
    if "service_date" in fields:
        fields["date"] = fields["service_date"]
    elif "document_date" in fields:
        fields["date"] = fields["document_date"]
    for key in ("invoice_number", "date", "currency", "stated_total", "provider"):
        if key not in fields:
            issues.append("UNRESOLVED_METADATA_" + key)
    return fields, sorted(set(issues))


def detect_candidates(words, document_id: str, sha256: str):
    """Locate labelled invoice lines; a match remains unverified and review-only.

    Expects at most one page, pixel coordinates, and ordered token boxes; all
    values originate from the authenticated PDF, never synthetic ground truth.
    """
    lines = _lines(words)
    headers = []
    for i, line in enumerate(lines):
        found = {}
        duplicate = False
        for word in line["words"]:
            key = ALIASES.get(word["text"].upper()) or ALIASES.get(word["text"])
            if key:
                if key in found:
                    duplicate = True
                found[key] = word
        if len(found) >= 5 and not duplicate:
            headers.append((i, found))
    if len(headers) != 1 or len(headers[0][1]) != 6:
        return {"fields": {}, "rows": [], "issues": ["TABLE_HEADER_AMBIGUOUS"],
                "header_fields": len(headers[0][1]) if headers else 0}
    header_index, header = headers[0]
    positions = {key: (w["bbox"][0] + w["bbox"][2]) / 2 for key, w in header.items()}
    fields, issues = _metadata(lines, header_index, document_id, sha256)
    rows = []
    for line in lines[header_index + 1:]:
        if line["mid"] - lines[header_index]["mid"] > 850:
            break
        if len(line["words"]) < 3:
            continue
        assigned = {key: [] for key in positions}
        for word in line["words"]:
            x = (word["bbox"][0] + word["bbox"][2]) / 2
            assigned[min(positions, key=lambda key: abs(x - positions[key]))].append(word)
        if sum(bool(group) for group in assigned.values()) < 3:
            continue
        item = {}
        for key, group in assigned.items():
            if not group:
                issues.append("MISSING_CELL_" + key)
                item[key] = None
                continue
            candidate = _anchor(group, document_id, sha256)
            if (len(group) > 1 or not re.fullmatch(PATTERNS[key], candidate["value"])
                    or candidate["ocr_confidence_uncalibrated"] < 0.65):
                issues.append("AMBIGUOUS_CELL_" + key)
            item[key] = candidate
        rows.append(item)
    if not rows:
        issues.append("NO_TABLE_ROWS")
    if len({row["id"]["value"] for row in rows if row.get("id")}) != len(rows):
        issues.append("DUPLICATE_OR_MISSING_LINE_IDENTITIES")
    if "service_date" not in fields:
        issues.append("SERVICE_DATE_NOT_EXPLICIT")
    return {"fields": fields, "rows": rows, "issues": sorted(set(issues)),
            "header_fields": len(header)}
