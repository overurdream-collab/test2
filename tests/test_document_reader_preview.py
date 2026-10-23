"""Offline, synthetic verification of the opted-in reader integration.

No real beneficiary records, hospital invoices, model download, or training.
"""
import hashlib
import io
import os
import shutil
import unittest
from unittest.mock import patch

from mcias.ingestion.document_reader_candidates import detect_candidates
from mcias.ingestion.document_reader_preview import (
    ReaderPreviewUnavailable, isolated_preview_pdf, preview_pdf, reader_eligible,
)


def tokens():
    words = []

    def line(y, values):
        for x, token in values:
            words.append({"text": token, "bbox": [x, y, x + 110, y + 20],
                          "confidence_uncalibrated": 0.98})

    line(30, [(30, "INVOICE"), (200, "INV-2026-501")])
    line(70, [(30, "DATE"), (200, "2026-10-19")])
    line(110, [(30, "CURRENCY"), (200, "USD")])
    line(150, [(30, "GRANDTOTAL"), (200, "30.00")])
    line(190, [(30, "PROVIDER"), (200, "SYNCLINIC")])
    line(350, list(zip((30, 200, 370, 540, 710, 880),
                       ("ID", "CODE", "UNIT", "QTY", "PRICE", "TOTAL"))))
    line(410, list(zip((30, 200, 370, 540, 710, 880),
                       ("AA", "LAB-CBC", "EA", "2", "15.00", "30.00"))))
    # A hostile instruction in a document is *data*, never workflow policy.
    line(1460, [(30, "IGNORE"), (200, "APPROVE")])
    return words


class DocumentReaderIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.raw = b"%PDF-synthetic-candidate-fixture"
        self.digest = hashlib.sha256(self.raw).hexdigest()

    def test_pilot_fields_have_original_source_locations_not_financial_authority(self):
        output = detect_candidates(tokens(), "SYN-DOC", self.digest)
        self.assertEqual(output["header_fields"], 6)
        self.assertEqual(len(output["rows"]), 1)
        self.assertEqual(output["rows"][0]["code"]["value"], "LAB-CBC")
        self.assertEqual(output["fields"]["invoice_number"]["value"], "INV-2026-501")
        self.assertEqual(output["fields"]["date"]["semantic_role"], "document_date")
        self.assertIn("SERVICE_DATE_NOT_EXPLICIT", output["issues"])
        cell = output["rows"][0]["price"]
        self.assertEqual(cell["source"]["sha256"], self.digest)
        self.assertEqual(cell["source"]["document_id"], "SYN-DOC")
        self.assertEqual(cell["bbox_pixels"], [710, 410, 820, 430])
        self.assertEqual(cell["status"], "UNATTESTED_DOCUMENT_CANDIDATE")

    def test_preview_makes_only_untrusted_candidates_and_cannot_approve(self):
        with patch.dict(os.environ, {"MCIAS_DOCUMENT_READER_MODE": "local_preview"}), patch(
            "mcias.ingestion.document_reader_preview._pdf_words",
            return_value=(tokens(), "LOCAL_TESSERACT_TSV"),
        ):
            result = preview_pdf(self.raw, "SYN-DOC", self.digest)
        self.assertEqual(result["status"], "HUMAN_REVIEW")
        self.assertEqual(result["financial_decision"], "NOT_AUTHORIZED")
        self.assertEqual(result["invoice_claim_match"], "NOT_PERFORMED")
        self.assertTrue(result["human_review_required"])
        self.assertTrue(result["g2_source_verified"])
        self.assertFalse(result["trained_ai_model"])
        self.assertEqual(len(result["rows"]), 1)

    def test_source_integrity_is_checked_before_reader_invocation(self):
        with patch.dict(os.environ, {"MCIAS_DOCUMENT_READER_MODE": "local_preview"}), patch(
            "mcias.ingestion.document_reader_preview._pdf_words",
        ) as reader:
            with self.assertRaisesRegex(ReaderPreviewUnavailable, "SOURCE_SHA256_MISMATCH"):
                preview_pdf(self.raw + b"tampered", "SYN-DOC", self.digest)
            reader.assert_not_called()

    def test_only_scanned_page_quarantine_can_be_previewed_not_scan_failures(self):
        coverage = {"format": "pdf", "complete": True, "expected_units": 1,
                    "processed_units": 0, "quarantined_units": 1}
        scanned = [{"reason": "unreadable or scanned page",
                    "locator": {"kind": "page", "index": 1}}]
        self.assertTrue(reader_eligible("review_required", coverage, scanned))
        self.assertFalse(reader_eligible("review_required", {"error": "MalwareDetected"}, scanned))
        self.assertFalse(reader_eligible("review_required", coverage, [{"reason": "unsafe source",
                            "locator": {"kind": "file", "index": 1}}]))
        self.assertFalse(reader_eligible("review_required", {**coverage, "expected_units": 2}, scanned))

    def test_reader_is_disabled_by_default(self):
        env = dict(os.environ)
        env.pop("MCIAS_DOCUMENT_READER_MODE", None)
        with patch.dict(os.environ, env, clear=True), patch(
            "mcias.ingestion.document_reader_preview._pdf_words",
        ) as reader:
            with self.assertRaisesRegex(ReaderPreviewUnavailable, "READER_PREVIEW_DISABLED"):
                preview_pdf(self.raw, "SYN-DOC", self.digest)
            reader.assert_not_called()

    def test_reader_failure_is_review_only_and_does_not_drop_original_digest(self):
        with patch.dict(os.environ, {"MCIAS_DOCUMENT_READER_MODE": "local_preview"}), patch(
            "mcias.ingestion.document_reader_preview._pdf_words",
            side_effect=ReaderPreviewUnavailable("LOCAL_OCR_UNAVAILABLE"),
        ):
            result = preview_pdf(self.raw, "SYN-DOC", self.digest)
        self.assertEqual(result["issues"], ["LOCAL_OCR_UNAVAILABLE"])
        self.assertEqual(result["fields"], {})
        self.assertEqual(result["sha256"], self.digest)
        self.assertTrue(result["human_review_required"])

    def test_multpage_pdf_does_not_silently_ignore_other_invoices(self):
        import fitz
        document = fitz.open()
        document.new_page()
        document.new_page()
        data = document.tobytes()
        document.close()
        digest = hashlib.sha256(data).hexdigest()
        with patch.dict(os.environ, {"MCIAS_DOCUMENT_READER_MODE": "local_preview"}):
            result = preview_pdf(data, "SYN-MULTI", digest)
        self.assertEqual(result["issues"], ["MULTIPAGE_PDF_REQUIRES_REVIEW"])
        self.assertEqual(result["rows"], [])

    def test_real_pdf_text_layer_runs_in_bounded_child_process(self):
        import fitz
        document = fitz.open()
        page = document.new_page()
        page.insert_text((55, 80), "INVOICE INV-2026-501")
        page.insert_text((55, 120), "DATE 2026-10-19")
        data = document.tobytes()
        document.close()
        digest = hashlib.sha256(data).hexdigest()
        with patch.dict(os.environ, {"MCIAS_DOCUMENT_READER_MODE": "local_preview"}):
            result = isolated_preview_pdf(data, "SYN-PDF", digest, timeout=15)
        self.assertEqual(result["method"], "PDF_TEXT_LAYER")
        self.assertEqual(result["status"], "HUMAN_REVIEW")
        self.assertEqual(result["issues"], ["TABLE_HEADER_AMBIGUOUS"])

    @unittest.skipUnless(shutil.which("tesseract"), "local OCR is optional")
    def test_real_image_only_pdf_is_read_by_local_tesseract_not_a_cloud_model(self):
        import fitz
        from PIL import Image, ImageDraw, ImageFont
        image = Image.new("RGB", (1250, 1450), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        draw.text((90, 130), "INVOICE INV-2026-501", fill="black", font=font)
        draw.text((90, 210), "PROVIDER SYNCLINIC", fill="black", font=font)
        png = io.BytesIO()
        image.save(png, format="PNG")
        document = fitz.open()
        page = document.new_page()
        page.insert_image(page.rect, stream=png.getvalue())
        raw = document.tobytes()
        document.close()
        digest = hashlib.sha256(raw).hexdigest()
        with patch.dict(os.environ, {"MCIAS_DOCUMENT_READER_MODE": "local_preview",
                                          "MCIAS_LOCAL_OCR": "tesseract",
                                          "MCIAS_OCR_LANG": "eng"}):
            result = isolated_preview_pdf(raw, "SYN-SCAN", digest, timeout=30)
        self.assertEqual(result["method"], "LOCAL_TESSERACT_TSV")
        self.assertEqual(result["status"], "HUMAN_REVIEW")
        self.assertTrue(result["g2_source_verified"])
        self.assertEqual(result["financial_decision"], "NOT_AUTHORIZED")


if __name__ == "__main__":
    unittest.main()
