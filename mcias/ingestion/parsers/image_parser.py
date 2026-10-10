"""Image extraction with optional offline OCR and mandatory quarantine on uncertainty."""
from mcias.ingestion.schemas import Extraction, ExtractedRecord, Locator
from mcias.ingestion.quarantine import item
from mcias.ingestion.ocr_engine import recognize, OCRUnavailable

def parse(data: bytes) -> Extraction:
    result = Extraction(format="image", units_total=1)
    try:
        text = recognize(data)
    except (OCRUnavailable, UnicodeError):
        text = ""
    if not text:
        result.quarantined.append(item("local OCR unavailable or unreadable", "page", 1))
    else:
        result.records.append(ExtractedRecord(Locator("page", 1), {"text": text}, confidence=0.5))
        result.units_processed = 1
    return result
