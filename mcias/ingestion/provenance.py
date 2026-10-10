"""Stable source coordinates; no inferred positions."""
from mcias.ingestion.schemas import Locator

def locator_dict(locator: Locator) -> dict:
    return {"kind": locator.kind, "index": locator.index, "row": locator.row, "column": locator.column}
