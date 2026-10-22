"""Coverage accounting: every source unit is extracted or quarantined."""
from mcias.ingestion.schemas import Extraction

def manifest(result: Extraction) -> dict:
    result_manifest = {"format": result.format, "expected_units": result.units_total, "processed_units": result.units_processed, "quarantined_units": len(result.quarantined), "complete": result.complete}
    if result.format == "xlsx":
        result_manifest["worksheet_inventory"] = result.worksheet_inventory
    return result_manifest
