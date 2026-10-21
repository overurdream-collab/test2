"""Synthetic real image/OCR/scanned-PDF compatibility, no model qualification."""
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
import pymupdf

from mcias.ingestion.ocr_engine import recognize
from mcias.ingestion.parsers.image_parser import parse as parse_image
from mcias.ingestion.parsers.pdf_parser import parse as parse_pdf


def _image():
    image = Image.new("RGB", (1200, 240), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 80), "SYNTHETIC INVOICE 12345", fill="black", font=ImageFont.load_default(size=48))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_real_pillow_image_ocr_and_image_parser(monkeypatch):
    monkeypatch.setenv("MCIAS_LOCAL_OCR", "tesseract")
    monkeypatch.setenv("MCIAS_OCR_LANG", "eng")
    data = _image()
    assert "INVOICE 12345" in recognize(data)
    result = parse_image(data)
    assert not result.quarantined
    assert "INVOICE 12345" in result.records[0].values["text"]
    assert result.records[0].confidence == 0.5  # OCR remains untrusted


def test_real_scanned_pdf_render_ocr_and_provenance(monkeypatch):
    monkeypatch.setenv("MCIAS_LOCAL_OCR", "tesseract")
    monkeypatch.setenv("MCIAS_OCR_LANG", "eng")
    with pymupdf.open() as document:
        page = document.new_page(width=600, height=120)
        page.insert_image(page.rect, stream=_image())
        data = document.tobytes()
    result = parse_pdf(data)
    assert result.units_processed == result.units_total == 1
    assert not result.quarantined
    assert "INVOICE 12345" in result.records[0].values["text"]
    assert result.records[0].locator.kind == "page"
    assert result.records[0].locator.index == 1
    assert result.records[0].confidence == 0.5
