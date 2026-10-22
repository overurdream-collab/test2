"""Phase 2A contract and privacy tests; no database required."""
import inspect
import pytest
from mcias.audit_contract import validate_event, clean_details, new_request_attempt_id
from mcias.audit_writer import write_event, record_outcome_independent

@pytest.mark.parametrize("field", ["action", "resource_type", "resource_id"])
@pytest.mark.parametrize("secret", ["Patient Ahmed Ali", "diagnosis diabetes", "Rx morphine",
                                      "Bearer supersecret", "اسم المريض محمد", "وصفة دواء"])
def test_sensitive_data_rejected_in_primary_fields(field, secret):
    args = dict(action="test_event", resource_type="test", resource_id="opaque-123", outcome="success")
    args[field] = secret
    with pytest.raises(ValueError):
        validate_event(**args)

def test_details_never_accept_sensitive_free_text():
    d = {"patient_name": "Patient Ahmed Ali", "diagnosis": "diabetes",
         "prescription": "Rx morphine", "secret": "Bearer abc",
         "contract_number": "Patient Ahmed Ali", "status": "diagnosis",
         "reason_code": "Bearer abc", "version": 2, "effective_from": "2026-02-31"}
    assert clean_details(d) == {"version": 2}

def test_valid_contract_values():
    validate_event("contract_revision_denied", "contract_version", None, "denied")
    assert clean_details({"reason_code":"permission_denied", "status":"approved"}) == {
        "reason_code":"permission_denied", "status":"approved"}

def test_attempt_id_unique_across_calls():
    ids = [new_request_attempt_id() for _ in range(150)]
    assert len(ids) == len(set(ids))
    from uuid import UUID
    assert all(UUID(x).version == 4 for x in ids)

def test_original_public_signatures_preserved():
    assert list(inspect.signature(write_event).parameters) == [
        "db", "actor", "organization_id", "action", "resource_type", "resource_id", "outcome", "details"]
    assert list(inspect.signature(record_outcome_independent).parameters) == [
        "bind", "actor_id", "organization_id", "action", "resource_type", "resource_id", "outcome", "details"]
