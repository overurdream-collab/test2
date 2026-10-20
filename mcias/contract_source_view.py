"""C35 Phase 1: immutable, deterministic view of already extracted G2 source blocks.

Not wired to inference, candidate generation, validation or financial actions.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Mapping

from mcias.contract_intelligence import ContractExtractionError


def _digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def make_source_view(blocks, *, source_sha256):
    """Index literal, nonempty G2 fields; no values are synthesized or normalized.

    IDs incorporate source digest, record, full locator, field name and ordinal;
    duplicate records/locations/field addresses fail closed. Caller must supply
    the original document's SHA-256 (the same one used by Validator).
    """
    if not isinstance(source_sha256, str) or len(source_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in source_sha256):
        raise ContractExtractionError("invalid source digest")
    if not isinstance(blocks, list) or not blocks or len(blocks) > 40:
        raise ContractExtractionError("invalid source blocks")
    entries, addresses, identifiers = [], set(), set()
    for block in blocks:
        if not isinstance(block, dict) or not isinstance(block.get("record_id"), str):
            raise ContractExtractionError("invalid source block")
        record_id, locator, fields = block["record_id"], block.get("locator"), block.get("fields")
        if not record_id or not isinstance(locator, dict) or not isinstance(fields, dict):
            raise ContractExtractionError("invalid source block")
        if locator.get("kind") not in {"page", "sheet", "row", "image"} or (
            type(locator.get("index")) is not int or locator["index"] < 1):
            raise ContractExtractionError("invalid locator")
        if locator["kind"] in {"sheet", "row"} and (
            type(locator.get("row")) is not int or locator["row"] < 1):
            raise ContractExtractionError("row identity required")
        if not all(isinstance(k, str) and k and isinstance(v, str) for k, v in fields.items()):
            raise ContractExtractionError("invalid source fields")
        # Source blocks may represent different nonoverlapping page segments.
        address = (record_id, _digest(locator))
        if address in addresses:
            raise ContractExtractionError("duplicate record locator")
        addresses.add(address)
        group_id = "g_" + _digest([source_sha256, record_id, locator])[:32]
        for ordinal, (name, value) in enumerate(fields.items()):
            if not value.strip():
                continue  # make_source_blocks already omits blank values
            # Field names may be literal A1 addresses when G2 provides them.
            field_locator = {**locator, "field": name}
            identifier = "f_" + _digest([source_sha256, record_id, locator, name])[:32]
            if identifier in identifiers:
                raise ContractExtractionError("duplicate field identifier")
            identifiers.add(identifier)
            entries.append({"id": identifier, "group_id": group_id,
                            "record_id": record_id, "locator": field_locator,
                            "source_locator": dict(locator), "field_name": name,
                            "field_type": "text", "value": value,
                            "source_sha256": source_sha256})
    return {"source_sha256": source_sha256, "fields": entries}


def lookup_source_field(view, field_id):
    """Fail closed: never resolve an absent or ambiguous source reference."""
    if not isinstance(field_id, str) or not isinstance(view, dict):
        raise ContractExtractionError("invalid field reference")
    matches = [f for f in view.get("fields", []) if f["id"] == field_id]
    if len(matches) != 1:
        raise ContractExtractionError("unknown or ambiguous field reference")
    return matches[0]
