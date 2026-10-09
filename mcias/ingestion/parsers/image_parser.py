"""Image ingestion requires an approved local OCR engine; never fabricate text."""
from mcias.ingestion.schemas import Extraction
from mcias.ingestion.quarantine import item

def parse(data: bytes) -> Extraction:
    return Extraction(format="image", units_total=1, quarantined=[item("local OCR engine not configured", "page", 1)])
