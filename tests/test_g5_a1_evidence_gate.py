"""Pure consumer contract tests; native producer/PG16 verification is separate."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from hashlib import sha256
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from mcias.audit_agents import _a1_review_evidence
from mcias.audit_engine import PolicyBlocked
from mcias.audit_service import run_audit, _review_findings_identity


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


@pytest.fixture
def consumer(monkeypatch):
    claim = SimpleNamespace(id="claim-1", organization_id="org-1", extracted_record_id="claim-row",
        service_date=date(2026, 6, 1), service_code="SYN-SERVICE", currency="USD",
        claimed_amount=Decimal("100"), source_values={"quantity": "1", "unit_price": "100", "unit": "UNIT"})
    source = {"document_id": "invoice-1", "sha256": "1" * 64, "locator": "csv:row:2"}
    line = {"line_item_id": "line-1", "kind": "service", "code": "SYN-SERVICE", "unit": "UNIT",
        "currency": "USD", "quantity": "2", "unit_price": "60", "line_total": "110",
        "source_record_id": "invoice-row", "source_file_id": "invoice-file", "source": source,
        "field_sources": {"quantity": {**source, "source_record_id": "invoice-row", "locator": "csv:row:2:field:quantity"}}}
    evidence = {"claim": {"source_record_id": "claim-row", "source_scope": {"sheet_type": "CLAIMS"}},
        "invoice": {"document_id": "invoice-1", "stated_total": "115", "source": source},
        "invoice_lines": [line], "arithmetic_qualification": {"source_qualified": True,
            "qualified": False, "gaps": ["explicit_adjustment_context", "approved_arithmetic_rule"]},
        "unit_price_authority": "NOT_ESTABLISHED"}
    packet = {"schema_version": "mcias.a1.review.v1", "tenant_id": claim.organization_id, "claim_id": claim.id,
        "audit_run_id": "SYN-RUN-1", "a1_input_fingerprint": "2" * 64, "a1_output_fingerprint": "3" * 64,
        "source_evidence": deepcopy(evidence), "source_evidence_fingerprint": digest(evidence),
        "classification_is_final": False, "financial_decision_authorized": False,
        "findings": [{"origin": "RULE_ENGINE", "status": "PASS"}]}
    calls = []
    module = ModuleType("mcias.agents.a1_trusted_input")
    class SourceBlocked(ValueError):
        pass
    module.A1AccessDenied = SourceBlocked
    module.A1SourceBlocked = SourceBlocked
    def rebuild(db, actor, claim_id, store, *, run_id):
        calls.append((claim_id, store, run_id))
        return {"source_evidence": deepcopy(evidence)}
    module.build_a1_snapshot = rebuild
    monkeypatch.setitem(sys.modules, module.__name__, module)
    return claim, packet, evidence, calls, module


def review(consumer, packet=None, store=True):
    claim, original, _, _, _ = consumer
    return _a1_review_evidence(None, claim, object(), original if packet is None else packet, object() if store else None)


def test_native_values_are_recomputed_independently_and_remain_unresolved(consumer):
    result = review(consumer)
    assert result["source_evidence_verified"] is True
    assert result["audit_state"] == "UNRESOLVED"
    assert result["a1_input_fingerprint_verified"] is False
    assert result["a1_output_fingerprint_verified"] is False
    assert result["gaps"] == ["explicit_adjustment_context_missing", "approved_arithmetic_rule_missing"]
    signals = {signal["code"]: signal for signal in result["signals"]}
    assert set(signals) == {"invoice_line_arithmetic_conflict", "invoice_total_arithmetic_conflict",
        "invoice_claim_amount_conflict", "invoice_quantity_conflict", "invoice_unit_price_conflict"}
    assert signals["invoice_line_arithmetic_conflict"]["comparison_value"] == "120"
    assert signals["invoice_claim_amount_conflict"]["comparison_value"] == "115"
    assert all(signal["source_record_ids"] for signal in signals.values())
    assert "payable" not in result and "deductions" not in result


@pytest.mark.parametrize("field,value,reason", [
    ("schema_version", "other", "a1_packet_contract_invalid"),
    ("tenant_id", "org-2", "a1_packet_claim_scope_mismatch"),
    ("claim_id", "claim-2", "a1_packet_claim_scope_mismatch"),
    ("audit_run_id", "", "a1_packet_fingerprint_or_run_invalid"),
    ("audit_run_id", "run with spaces", "a1_packet_fingerprint_or_run_invalid"),
    ("a1_input_fingerprint", "x" * 64, "a1_packet_fingerprint_or_run_invalid"),
    ("a1_output_fingerprint", "3" * 63, "a1_packet_fingerprint_or_run_invalid"),
    ("classification_is_final", True, "a1_packet_authority_invalid"),
    ("financial_decision_authorized", True, "a1_packet_authority_invalid"),
    ("source_evidence_fingerprint", "0" * 64, "a1_packet_source_fingerprint_mismatch"),
])
def test_packet_scope_and_integrity_fail_before_source_access(consumer, field, value, reason):
    packet = deepcopy(consumer[1]); packet[field] = value
    result = review(consumer, packet)
    assert result["audit_state"] == "UNRESOLVED" and result["gaps"] == [reason]
    assert result["source_evidence_verified"] is False and result["signals"] == []
    assert consumer[3] == []


@pytest.mark.parametrize("field,value", [
    ("quantity", "3"), ("unit_price", "70"), ("line_total", "120"),
    ("currency", "EUR"), ("source_record_id", "other-row"),
    ("source", {"document_id": "other-document", "sha256": "f" * 64, "locator": "csv:row:9"}),
    ("field_sources", {"quantity": {"source_record_id": "other-row", "locator": "page:1"}}),
])
def test_changed_values_and_source_cannot_be_authorized_by_rehashing(consumer, field, value):
    packet = deepcopy(consumer[1]); packet["source_evidence"]["invoice_lines"][0][field] = value
    packet["source_evidence_fingerprint"] = digest(packet["source_evidence"])
    result = review(consumer, packet)
    assert result["gaps"] == ["a1_packet_source_values_mismatch"]
    assert result["audit_state"] == "UNRESOLVED" and not result["source_evidence_verified"]
    assert not result["signals"] and len(consumer[3]) == 1


def test_ocr_or_qualification_flags_cannot_replace_original_native_rows(consumer):
    packet = deepcopy(consumer[1])
    packet["source_evidence"]["invoice_lines"][0]["source"]["locator"] = "page:1:whole-page"
    packet["source_evidence"]["arithmetic_qualification"] = {"source_qualified": True, "qualified": True, "gaps": []}
    packet["source_evidence_fingerprint"] = digest(packet["source_evidence"])
    assert review(consumer, packet)["gaps"] == ["a1_packet_source_values_mismatch"]


def test_packet_without_server_store_is_explicitly_unresolved(consumer):
    result = review(consumer, store=False)
    assert result["gaps"] == ["source_verification_unavailable"]
    assert not result["source_evidence_verified"] and consumer[3] == []


def test_original_or_permission_failure_cannot_become_a_proof(consumer):
    def blocked(*args, **kwargs):
        raise consumer[4].A1SourceBlocked("do not leak source values")
    consumer[4].build_a1_snapshot = blocked
    result = review(consumer)
    assert result["gaps"] == ["a1_original_source_verification_failed"]
    assert "do not leak" not in json.dumps(result)
    assert result["signals"] == []


def test_retry_and_unused_advisory_status_do_not_change_validated_finding(consumer):
    first = review(consumer)
    packet = deepcopy(consumer[1])
    packet.update(produced_at="2099-01-01T00:00:00Z", findings=[{"origin": "AI_ADVISORY", "status": "VIOLATION_PROVEN"}])
    assert review(consumer, packet) == first


def test_multi_line_invoice_does_not_invent_claim_line_mapping(consumer):
    evidence = consumer[2]
    line = deepcopy(evidence["invoice_lines"][0]); line.update(line_item_id="line-2", source_record_id="row-2")
    evidence["invoice_lines"].append(line)
    packet = deepcopy(consumer[1]); packet["source_evidence"] = deepcopy(evidence)
    packet["source_evidence_fingerprint"] = digest(evidence)
    codes = {signal["code"] for signal in review(consumer, packet)["signals"]}
    assert "invoice_quantity_conflict" not in codes and "invoice_unit_price_conflict" not in codes


def test_financial_service_cannot_consume_advisory_packet():
    with pytest.raises(PolicyBlocked, match="restricted to advisory"):
        run_audit(None, None, "claim", a1_review_packet={})


def identity_findings(consumer):
    return {"agents": [{"agent": "evidence", "rule_version": 2, "audit_state": "UNRESOLVED",
        "a1_evidence": review(consumer)}], "audit_state": "UNRESOLVED",
        "source_evidence": {"source_record_id": "claim-row", "source_sha256": "f" * 64},
        "reference_certificates": [{"family": "tariff", "version": 1, "effective_from": "2026-01-01"}]}


@pytest.mark.parametrize("key,value", [("a1_input_fingerprint", "a" * 64),
    ("a1_output_fingerprint", "b" * 64), ("audit_run_id", "SYN-FRESH-RUN")])
def test_result_identity_ignores_only_unverified_a1_trace(consumer, key, value):
    findings = identity_findings(consumer)
    original = deepcopy(findings)
    retry = deepcopy(findings); retry["agents"][0]["a1_evidence"][key] = value
    assert _review_findings_identity(retry) == _review_findings_identity(findings)
    assert findings == original
    assert findings["agents"][0]["a1_evidence"][key] != value


@pytest.mark.parametrize("path,value", [
    (("source_evidence", "source_record_id"), "other-row"),
    (("source_evidence", "source_sha256"), "e" * 64),
    (("reference_certificates", 0, "version"), 2),
    (("reference_certificates", 0, "effective_from"), "2026-06-01"),
    (("audit_state",), "MATCH_VERIFIED"),
    (("agents", 0, "rule_version"), 3),
    (("agents", 0, "audit_state"), "VIOLATION_PROVEN"),
    (("agents", 0, "a1_evidence", "source_evidence_fingerprint"), "d" * 64),
    (("agents", 0, "a1_evidence", "source_evidence_verified"), False),
    (("agents", 0, "a1_evidence", "a1_input_fingerprint_verified"), True),
    (("agents", 0, "a1_evidence", "a1_output_fingerprint_verified"), True),
    (("agents", 0, "a1_evidence", "signals", 0, "observed_value"), "999"),
    (("agents", 0, "a1_evidence", "signals", 0, "source_record_ids"), ["other-row"]),
    (("agents", 0, "a1_evidence", "gaps"), []),
])
def test_result_identity_preserves_source_rules_versions_states_and_verification(consumer, path, value):
    findings = identity_findings(consumer)
    changed = deepcopy(findings)
    target = changed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert _review_findings_identity(changed) != _review_findings_identity(findings)


def test_identity_does_not_strip_similar_fields_outside_exact_evidence_path(consumer):
    findings = identity_findings(consumer)
    findings["a1_output_fingerprint"] = "root-trace"
    findings["agents"].append({"agent": "tariff", "a1_evidence": {"a1_output_fingerprint": "tariff-trace"}})
    result = _review_findings_identity(findings)
    assert result["a1_output_fingerprint"] == "root-trace"
    assert result["agents"][1]["a1_evidence"]["a1_output_fingerprint"] == "tariff-trace"
    assert "a1_output_fingerprint" not in result["agents"][0]["a1_evidence"]


def test_identity_without_packet_has_identical_content_and_independent_copy():
    findings = {"audit_state": "MATCH_VERIFIED", "agents": [{"agent": "evidence", "rule_version": 2}]}
    result = _review_findings_identity(findings)
    assert result == findings and result is not findings
    result["agents"][0]["rule_version"] = 9
    assert findings["agents"][0]["rule_version"] == 2
