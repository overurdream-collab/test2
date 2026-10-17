"""Synthetic-only contract model constrained-output syntax checks (no real model claims)."""
import ast
import json
import re
from pathlib import Path


def test_diagnostic_model_decimal_amount_schema_without_percent_sign():
    source = Path(__file__).resolve().parents[1] / "scripts" / "contract_ai_benchmark.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    assignment = next(node for node in tree.body
                      if isinstance(node, ast.Assign) and
                      any(isinstance(target, ast.Name) and target.id == "CLAUSE_SCHEMA"
                          for target in node.targets))
    schema = ast.literal_eval(assignment.value)
    clauses = schema["properties"]["clauses"]
    amount = clauses["items"]["properties"]["amount"]
    assert amount["anyOf"][1] == {"type": "null"}
    pattern = amount["anyOf"][0]["pattern"]
    assert re.fullmatch(pattern, "20")
    assert re.fullmatch(pattern, "5000")
    assert re.fullmatch(pattern, "7000")
    assert re.fullmatch(pattern, "20.25")
    for invalid in ("20%", "20 percent", "-1", "2.12345", "2026-01-01", ""):
        assert re.fullmatch(pattern, invalid) is None
    assert clauses["minItems"] == 1  # pre-existing forced diagnostic only
    assert schema["additionalProperties"] is False
    assert json.loads(json.dumps(schema)) == schema
