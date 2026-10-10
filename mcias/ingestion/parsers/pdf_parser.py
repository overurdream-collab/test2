"""PDF page accounting: scanned/unreadable pages are isolated, never guessed."""
import io
from pypdf import PdfReader
from mcias.ingestion.schemas import Extraction, ExtractedRecord, Locator
from mcias.ingestion.quarantine import item

def parse(data: bytes) -> Extraction:
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise ValueError("encrypted PDF requires explicit review")
    if len(reader.pages) > 2000:
        raise ValueError("PDF page limit exceeded")
    result = Extraction(format="pdf")
    for index, page in enumerate(reader.pages, start=1):
        result.units_total += 1
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if len(text) > 2_000_000:
            result.quarantined.append(item("page text exceeds limit", "page", index))
        elif not text.strip():
            result.quarantined.append(item("unreadable or scanned page", "page", index))
        else:
            result.records.append(ExtractedRecord(Locator("page", index), {"text": text}))
            result.units_processed += 1
    return result
