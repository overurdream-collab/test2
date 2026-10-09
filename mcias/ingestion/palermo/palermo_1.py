"""Palermo-1: extraction completeness and review routing, not financial decisions."""
from mcias.ingestion.manifest import manifest

def review(extraction):
    coverage = manifest(extraction)
    return {"status": "review_required" if extraction.quarantined or not extraction.complete else "extracted", "coverage": coverage, "findings": extraction.quarantined}
