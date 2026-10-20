#!/usr/bin/env python3
"""DG-002: compare OCR fields and source-locator quality. Stdlib; no OCR/model inference.

Only authored synthetic gold is accepted by this CLI; do not use output to elevate G2/A1 trust.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


def canonical(value: str) -> str:
    """Preserve Arabic digits, medication doses, separators, case and medical meaning."""
    if not isinstance(value, str):
        raise ValueError("Field and text values must be strings")
    return unicodedata.normalize("NFC", value).strip()


def edit_distance(a, b) -> int:
    prev = list(range(len(b) + 1))
    for i, char in enumerate(a, 1):
        curr = [i]
        for j, candidate in enumerate(b, 1):
            curr.append(min(curr[-1] + 1, prev[j] + 1, prev[j - 1] + (char != candidate)))
        prev = curr
    return prev[-1]


def bbox_iou(a, b) -> float:
    if not (isinstance(a, list) and isinstance(b, list) and len(a) == len(b) == 4):
        return 0.0
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in a + b):
        return 0.0
    ax, ay, ar, ab = a
    bx, by, br, bb = b
    if ar <= ax or ab <= ay or br <= bx or bb <= by:
        return 0.0
    area_a = (ar - ax) * (ab - ay)
    area_b = (br - bx) * (bb - by)
    inter = max(0, min(ar, br) - max(ax, bx)) * max(0, min(ab, bb) - max(ay, by))
    return inter / (area_a + area_b - inter)


def index_by(rows, key, context):
    indexed = {}
    for row in rows:
        ident = row[key]
        if ident in indexed:
            raise ValueError("Duplicate " + context + ": " + str(ident))
        indexed[ident] = row
    return indexed


def fraction(n, total):
    return round(n / total, 6) if total else None


def evaluate(gold: dict, prediction: dict) -> dict:
    expected = index_by(gold["documents"], "id", "gold document")
    received = index_by(prediction["documents"], "id", "prediction document")
    total = exact = aligned = exact_aligned = held = unsafe = invented = 0
    char_dist = char_count = word_dist = word_count = 0
    by_language = defaultdict(lambda: {"expected": 0, "exact": 0, "source_aligned": 0, "held": 0})
    by_kind = defaultdict(lambda: {"expected": 0, "exact": 0, "source_aligned": 0, "held": 0})
    details = []
    for doc_id, record in expected.items():
        found = received.get(doc_id, {"fields": [], "pages": []})
        if doc_id in received and found.get("sha256") != record["sha256"]:
            raise ValueError("SOURCE_SHA256_MISMATCH " + doc_id)
        if not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
            raise ValueError("INVALID_GOLD_SHA " + doc_id)
        fields = index_by(record["fields"], "field_id", "gold field")
        candidates = index_by(found.get("fields", []), "field_id", "predicted field")
        invented += len(set(candidates) - set(fields))
        language = record.get("language", "unknown")
        for field_id, truth in fields.items():
            got = candidates.get(field_id)
            kind = truth["kind"]
            truth_value = canonical(truth["value"])
            value_ok = bool(got and canonical(got["value"]) == truth_value)
            source_ok = bool(got and got.get("page") == truth.get("page")
                             and got.get("row_id") == truth.get("row_id")
                             and bbox_iou(got.get("bbox"), truth.get("bbox")) >= 0.5)
            review = not got or got.get("review_required") is not False
            wrong_accepted = bool(got and not review and (not value_ok or not source_ok))
            total += 1
            exact += int(value_ok)
            aligned += int(source_ok)
            exact_aligned += int(value_ok and source_ok)
            held += int(review)
            unsafe += int(wrong_accepted)
            for counters in (by_kind[kind], by_language[language]):
                counters["expected"] += 1
                counters["exact"] += int(value_ok)
                counters["source_aligned"] += int(source_ok)
                counters["held"] += int(review)
            details.append({"document_id": doc_id, "field_id": field_id, "kind": kind,
                            "language": language, "exact_value": value_ok,
                            "correct_page_row_and_iou": source_ok,
                            "referred_to_review": review, "unsafe_accepted": wrong_accepted,
                            "bbox_iou": round(bbox_iou(got.get("bbox"), truth.get("bbox")), 6) if got else 0.0})
        gold_pages = index_by(record.get("pages", []), "page", "gold page")
        predicted_pages = index_by(found.get("pages", []), "page", "predicted page")
        for page_id, pg in gold_pages.items():
            gt = canonical(pg["text"])
            pt = canonical(predicted_pages.get(page_id, {"text": ""})["text"])
            char_gt, char_pt = "".join(gt.split()), "".join(pt.split())
            tokens_gt, tokens_pt = gt.split(), pt.split()
            char_dist += edit_distance(char_gt, char_pt)
            char_count += len(char_gt)
            word_dist += edit_distance(tokens_gt, tokens_pt)
            word_count += len(tokens_gt)
    invented += sum(len(d.get("fields", [])) for k, d in received.items() if k not in expected)
    types = {k: {**v, "field_exact_rate": fraction(v["exact"], v["expected"]),
                 "source_aligned_rate": fraction(v["source_aligned"], v["expected"])}
             for k, v in by_kind.items()}
    languages = {k: {**v, "field_exact_rate": fraction(v["exact"], v["expected"]),
                     "source_aligned_rate": fraction(v["source_aligned"], v["expected"])}
                 for k, v in by_language.items()}
    return {"status": "DG002_SCORING_ONLY_NOT_MODEL_QUALIFICATION",
            "engine": prediction.get("engine", "UNSPECIFIED"),
            "documents_expected": len(expected),
            "fields_expected": total, "fields_exact": exact, "evidence_source_aligned": aligned,
            "fields_exact_and_aligned": exact_aligned,
            "unsafe_accepted_fields": unsafe, "review_or_missing_fields": held,
            "invented_extra_field_ids": invented,
            "field_exact_rate": fraction(exact, total),
            "field_exact_and_source_aligned_rate": fraction(exact_aligned, total),
            "review_or_missing_rate": fraction(held, total),
            "cer_whitespace_ignored": fraction(char_dist, char_count),
            "wer_whitespace_tokenized": fraction(word_dist, word_count),
            "by_language": languages, "by_kind": types, "details": details,
            "performance": {k: prediction.get(k) for k in
                            ("runtime_seconds", "peak_rss_mb", "peak_vram_mb")},
            "scope": "synthetic comparison; no real-world validation, model inference or G2/A1 source qualification"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", required=True)
    parser.add_argument("--prediction", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    pred = json.loads(Path(args.prediction).read_text(encoding="utf-8"))
    report = evaluate(gold, pred)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "fields_expected", "fields_exact",
                                             "fields_exact_and_aligned", "unsafe_accepted_fields",
                                             "invented_extra_field_ids")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
