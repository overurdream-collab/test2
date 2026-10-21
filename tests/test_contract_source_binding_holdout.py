"""Independent source-binding holdout; hand-written candidates, no model inference.

These cases measure validator containment, not model extraction precision/recall.
All sources and identities are synthetic and separate from frozen C33/C34 gold.
"""
from hashlib import sha256

import pytest

from mcias.contract_intelligence import make_source_blocks, validate_candidates


FIELDS = {
    "provider": "N7", "service": "LAB", "unit_price": "500", "currency": "USD",
    "effective_from": "2026-01-01", "effective_until": "2027-01-01",
}


def evaluate(fields, kind):
    if kind == "page":
        values = {"text": (
            f"Provider {fields['provider']} service {fields['service']} "
            f"unit price {fields['unit_price']} {fields['currency']} "
            f"effective {fields['effective_from']} until {fields['effective_until']}."
        )}
        locator = {"kind": "page", "index": 3}
        quote = values["text"]
    else:
        values = fields
        locator = {"kind": "sheet", "index": 2, "row": 17}
        quote = fields["unit_price"]
    blocks = make_source_blocks([{
        "id": "HOLDOUT-LITERAL-17", "locator": locator, "values": values,
    }])
    candidate = {
        "record_id": "HOLDOUT-LITERAL-17", "quote": quote,
        "section": "tariffs", "logical_key": "N7:LAB", "rule_type": "amount",
        "amount": "500", "provider_code": "N7", "service_code": "LAB",
        "currency": "USD", "effective_from": "2026-01-01",
        "effective_until": "2027-01-01",
    }
    digest = sha256(repr(values).encode("utf-8")).hexdigest()
    return validate_candidates([candidate], blocks, source_sha256=digest,
                               model_id="SYN-NO-MODEL", model_revision="HAND-WRITTEN")[0]


@pytest.mark.parametrize("kind", ["page", "sheet"])
@pytest.mark.parametrize("field,unsupported_literal,error", [
    ("provider", "N70", "provider_not_in_source"),
    ("service", "LABORATORY", "service_not_in_source"),
    ("currency", "USDX", "currency_not_in_source"),
    ("effective_from", "2026-01-01x", "effective_start_not_in_source"),
    ("effective_until", "2027-01-01x", "effective_end_not_in_source"),
    ("unit_price", "1500", "numeric_not_in_source"),
    ("unit_price", "500.50", "numeric_not_in_source"),
])
def test_partial_source_literals_cannot_verify_a_different_value(kind, field, unsupported_literal, error):
    result = evaluate({**FIELDS, field: unsupported_literal}, kind)
    assert error in result["validation_errors"], result
    assert result["evidence_status"] == "needs_human_review"
    assert result["status"] == "DRAFT_ONLY"


@pytest.mark.parametrize("kind", ["page", "sheet"])
def test_complete_source_literals_preserve_draft_only_evidence(kind):
    result = evaluate(dict(FIELDS), kind)
    assert result["validation_errors"] == []
    assert result["evidence_status"] == "verified_source_anchor"
    assert result["status"] == "DRAFT_ONLY"
