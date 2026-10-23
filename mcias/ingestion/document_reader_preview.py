"""Opt-in local, read-only bridge from G2 originals to untrusted invoice candidates.

No cloud calls, model training, automatic invoice matching, financial decisions,
or promotion of OCR output to G2 source records occurs here.
"""
from __future__ import annotations

import csv
import hashlib
import io
import multiprocessing as mp
import os
import queue
import re
import subprocess

from mcias.ingestion.document_reader_candidates import detect_candidates

MAX_PDF_SIZE = 20 * 1024 * 1024
MAX_RASTER_PIXELS = 20_000_000
MAX_OCR_OUTPUT = 2_000_000
MAX_WORDS = 2_000


class ReaderPreviewUnavailable(ValueError):
    """No trustworthy preview can be produced from the supplied original."""


def reader_eligible(status: str, manifest: dict | None, quarantine: list[dict]):
    """Permit only previously scanned G2 originals, including one scanned page.

    A G2 parser error or generic quarantine can *never* authorize this reader.
    """
    if status == "extracted":
        return True
    return bool(status == "review_required" and manifest and
                manifest.get("format") == "pdf" and manifest.get("complete") is True and
                manifest.get("expected_units") == 1 and
                manifest.get("processed_units") == 0 and
                manifest.get("quarantined_units") == 1 and
                quarantine == [{"reason": "unreadable or scanned page",
                                "locator": {"kind": "page", "index": 1}}])


def _held(document_id, sha256, issue, method=None):
    return {
        "document_id": document_id, "sha256": sha256,
        "status": "HUMAN_REVIEW", "human_review_required": True,
        "financial_decision": "NOT_AUTHORIZED", "g2_source_verified": True,
        "reader": "isolated_dynamic_layout_pilot_v1", "trained_ai_model": False,
        "method": method, "fields": {}, "rows": [], "issues": [issue],
        "invoice_claim_match": "NOT_PERFORMED",
    }


def _pdf_words(data):
    """Single-page, bounded extraction. Scanned PDFs use local Tesseract TSV."""
    try:
        import fitz  # optional PyMuPDF, already used by G2 OCR
    except ImportError as exc:
        raise ReaderPreviewUnavailable("PDF_READER_NOT_INSTALLED") from exc

    try:
        document = fitz.open(stream=data, filetype="pdf")
        with document:
            if document.needs_pass:
                raise ReaderPreviewUnavailable("ENCRYPTED_PDF")
            if len(document) != 1:
                raise ReaderPreviewUnavailable("MULTIPAGE_PDF_REQUIRES_REVIEW")
            page = document[0]
            scale = 2.5
            if page.rect.width <= 0 or page.rect.height <= 0 or (
                page.rect.width * scale * page.rect.height * scale > MAX_RASTER_PIXELS
            ):
                raise ReaderPreviewUnavailable("PDF_PAGE_PIXEL_LIMIT")
            native = page.get_text("words")
            if native:
                words = []
                for x0, y0, x1, y1, token, *_ in native[:MAX_WORDS + 1]:
                    token = str(token).strip().strip("\u200e\u200f")
                    if token:
                        words.append({"text": token,
                                      "bbox": [round(x0 * scale), round(y0 * scale),
                                               round(x1 * scale), round(y1 * scale)],
                                      # Text-layer availability is NOT model accuracy.
                                      "confidence_uncalibrated": 1.0})
                if len(words) > MAX_WORDS:
                    raise ReaderPreviewUnavailable("TOO_MANY_PDF_WORDS")
                return words, "PDF_TEXT_LAYER"
            if os.environ.get("MCIAS_LOCAL_OCR") != "tesseract":
                raise ReaderPreviewUnavailable("LOCAL_OCR_DISABLED")
            raster = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            if raster.width * raster.height > MAX_RASTER_PIXELS:
                raise ReaderPreviewUnavailable("PDF_PAGE_PIXEL_LIMIT")
            png = raster.tobytes("png")
    except ReaderPreviewUnavailable:
        raise
    except (RuntimeError, ValueError, OSError) as exc:
        raise ReaderPreviewUnavailable("PDF_RENDER_FAILED") from exc

    language = os.environ.get("MCIAS_OCR_LANG", "eng")
    if not re.fullmatch(r"[a-zA-Z0-9_]+(?:\+[a-zA-Z0-9_]+)*", language):
        raise ReaderPreviewUnavailable("INVALID_LOCAL_OCR_LANGUAGE")
    try:
        process = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", language, "--psm", "6", "tsv"],
            input=png, capture_output=True, timeout=25, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        raise ReaderPreviewUnavailable("LOCAL_OCR_UNAVAILABLE") from exc
    if process.returncode or len(process.stdout) > MAX_OCR_OUTPUT:
        raise ReaderPreviewUnavailable("LOCAL_OCR_FAILED")
    try:
        reader = csv.DictReader(io.StringIO(process.stdout.decode("utf-8")), delimiter="\t")
        words = []
        for record in reader:
            token = (record.get("text") or "").strip().strip("\u200e\u200f")
            if not token:
                continue
            x, y, width, height = (int(record[key]) for key in ("left", "top", "width", "height"))
            if min(x, y, width, height) < 0 or x + width > raster.width or y + height > raster.height:
                raise ReaderPreviewUnavailable("OCR_BOX_OUTSIDE_PAGE")
            words.append({"text": token, "bbox": [x, y, x + width, y + height],
                          "confidence_uncalibrated": max(0.0, min(1.0, float(record["conf"]) / 100))})
            if len(words) > MAX_WORDS:
                raise ReaderPreviewUnavailable("TOO_MANY_OCR_WORDS")
        return words, "LOCAL_TESSERACT_TSV"
    except (KeyError, TypeError, ValueError, UnicodeError) as exc:
        raise ReaderPreviewUnavailable("MALFORMED_OCR_TSV") from exc


def preview_pdf(data: bytes, document_id: str, sha256: str):
    """Report source-located candidates, *never* evidence accepted by G5/A1.

    The caller must authorize access to raw sensitive document contents first.
    """
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ReaderPreviewUnavailable("SOURCE_SHA256_MISMATCH")
    if os.environ.get("MCIAS_DOCUMENT_READER_MODE") != "local_preview":
        raise ReaderPreviewUnavailable("READER_PREVIEW_DISABLED")
    if len(data) > MAX_PDF_SIZE or not data.startswith(b"%PDF-"):
        raise ReaderPreviewUnavailable("NOT_A_SUPPORTED_PDF")
    try:
        words, method = _pdf_words(data)
        if not words:
            return _held(document_id, sha256, "NO_DOCUMENT_WORDS", method)
        candidates = detect_candidates(words, document_id, sha256)
    except ReaderPreviewUnavailable as exc:
        return _held(document_id, sha256, str(exc))
    # The pilot has *never* been approved as a source of truth; no candidate
    # can transition an invoice or claim into an accepted/rejected state.
    return {
        **_held(document_id, sha256, "", method),
        "fields": candidates["fields"], "rows": candidates["rows"],
        "issues": candidates["issues"],
        "header_fields": candidates["header_fields"],
        "candidate_quality": "UNVALIDATED_FOR_REAL_INVOICES",
    }


def _preview_worker(data, document_id, sha256, output):
    try:
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024,) * 2)
            resource.setrlimit(resource.RLIMIT_CPU, (35, 36))
        except (ImportError, OSError, ValueError):
            pass
        output.put(preview_pdf(data, document_id, sha256))
    except Exception:
        # Never serialize exception messages or original PDF contents into logs.
        output.put(_held(document_id, sha256, "READER_WORKER_FAILED"))


def isolated_preview_pdf(data: bytes, document_id: str, sha256: str, timeout=40):
    """Keep untrusted PDF parsing out of the FastAPI process, like G2 parsing."""
    # Check source integrity before creating another process.
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ReaderPreviewUnavailable("SOURCE_SHA256_MISMATCH")
    context = mp.get_context("spawn")
    output = context.Queue(maxsize=1)
    worker = context.Process(target=_preview_worker,
                             args=(data, document_id, sha256, output), daemon=True)
    worker.start()
    try:
        try:
            return output.get(timeout=timeout)
        except queue.Empty:
            return _held(document_id, sha256, "READER_WORKER_TIMEOUT")
    finally:
        if worker.is_alive():
            worker.terminate()
        worker.join(timeout=3)
        if worker.is_alive():
            worker.kill()
            worker.join(timeout=3)
        output.close()
