"""Runtime LM Format Enforcer pattern probe; no tokenizer or pretrained model needed."""
import ast
import json
from pathlib import Path

from lmformatenforcer import JsonSchemaParser


def actual_c25_schema():
    src = Path(__file__).resolve().parents[1] / "scripts" / "contract_ai_benchmark.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "CLAUSE_SCHEMA" for t in n.targets))
    return ast.literal_eval(node.value)


def accepts(schema, document):
    parser = JsonSchemaParser(schema)
    for pos, char in enumerate(document):
        allowed = parser.get_allowed_characters()
        if char not in allowed:
            return False, pos, char, allowed[:60]
        parser = parser.add_character(char)
    return bool(parser.can_end()), None, None, None


def candidate(amount):
    clause = {
        "record_id": "SYN-AR-COPAY",
        "quote": "Patient copay 20 percent from 2026-01-01 until 2027-01-01.",
        "section": "cost_sharing",
        "rule_type": "percentage",
        "logical_key": "copay_percent",
        "amount": amount,
        "provider_code": None,
        "service_code": None,
        "currency": None,
        "effective_from": "2026-01-01",
        "effective_until": "2027-01-01",
    }
    return json.dumps({"clauses": [clause]}, ensure_ascii=False, separators=(",", ":"))


def test_lmfe_enforces_nullable_decimal_pattern_on_actual_c25_schema():
    schema = actual_c25_schema()
    amount = schema["properties"]["clauses"]["items"]["properties"]["amount"]
    assert amount["anyOf"][1] == {"type": "null"}
    assert amount["anyOf"][0] == {"type": "string", "pattern": r"^[0-9]+(\.[0-9]{1,4})?$"}
    for value in ("20", "20.5", "5000", None):
        ok, *details = accepts(schema, candidate(value))
        assert ok, (value, details)
    for value in ("20%", "20 percent", "2026-01-01"):
        ok, *details = accepts(schema, candidate(value))
        assert not ok, (value, details)
