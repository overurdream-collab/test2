import io
import pytest
from PIL import Image
from mcias.ingestion.ocr_evaluation import score
from mcias.ingestion.ocr_engine import OCRUnavailable, recognize
from mcias.ingestion.isolated_parser import isolated_parse
from mcias.ingestion.reader_agent import read

def test_ocr_disabled_fail_closed(monkeypatch):
    monkeypatch.delenv("MCIAS_LOCAL_OCR", raising=False)
    with pytest.raises(OCRUnavailable):
        recognize(b"not an image")

def test_ocr_golden_error_rate_exact():
    result=score([("ABC", "ABC"), ("ABCD", "ABXD")])
    assert result.samples == 2
    assert result.exact_matches == 1
    assert result.character_error_rate == pytest.approx(1/7)

def test_ocr_empty_golden_dataset_rejected():
    with pytest.raises(ValueError):
        score([])

def test_local_ocr_unavailable_image_is_quarantined(monkeypatch):
    monkeypatch.delenv("MCIAS_LOCAL_OCR", raising=False)
    image=Image.new("RGB", (20,20), "white")
    buffer=io.BytesIO()
    image.save(buffer,format="PNG")
    result=read(buffer.getvalue(), "scan.png")
    assert result.units_total == 1
    assert result.quarantined

def test_isolated_csv_parser_roundtrip():
    result=isolated_parse("csv", b"id,amount\nA,12\n")
    assert result.records[0].values["amount"] == "12"
    assert result.complete
