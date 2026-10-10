"""Coverage accounting: every source unit is extracted or quarantined."""
from mcias.ingestion.schemas import Extraction

def manifest(result: Extraction) -> dict:
    return {"format": result.format, "expected_units": result.units_total, "processed_units": result.units_processed, "quarantined_units": len(result.quarantined), "complete": result.complete}
