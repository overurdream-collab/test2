"""Stable source coordinates; no inferred positions."""
from mcias.ingestion.schemas import Locator

def locator_dict(locator: Locator) -> dict:
    result = {"kind": locator.kind, "index": locator.index, "row": locator.row, "column": locator.column}
    if locator.sheet_name is not None:
        result["sheet_name"] = locator.sheet_name
    return result
