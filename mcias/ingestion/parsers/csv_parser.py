"""CSV parser preserving row numbers and original text values."""
import csv
import io
from mcias.ingestion.schemas import Extraction, ExtractedRecord, Locator
from mcias.ingestion.quarantine import item

def parse(data: bytes) -> Extraction:
    text = data.decode("utf-8-sig", errors="strict")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    header = next(reader, None)
    if not header or any(not h.strip() for h in header) or len(set(header)) != len(header):
        raise ValueError("invalid CSV header")
    result = Extraction(format="csv")
    for row in reader:
        result.units_total += 1
        if len(row) != len(header):
            result.quarantined.append(item("column count mismatch", "row", reader.line_num))
            continue
        result.records.append(ExtractedRecord(Locator("row", reader.line_num), dict(zip(header, row))))
        result.units_processed += 1
    return result
