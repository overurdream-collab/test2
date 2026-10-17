"""Synthetic-only shape validation; no G3/ReferencePoint writes or finance."""
from datetime import date
import pytest
from pydantic import ValidationError
from mcias.agents.a1_fee_reference_contract import ProposedAdditionalFeeReference


def payload():
    return {
        "organization_id": "SYN-ORG",
        "provider_code": "SYN-PROVIDER",
        "contract_version_id": "SYN-CV-ID",
        "contract_version": 2,
        "fee_code": "SYN-ADMIN",
        "unit": "invoice",
        "unit_price": "10.2500",
        "currency": "YER",
        "effective_from": date(2026, 1, 1),
        "effective_until": date(2027, 1, 1),
        "clause_source": {
            "document_id": "SYN-CONTRACT-DOC",
            "sha256": "a" * 64,
            "locator": "pdf:page:2:line:5",
        },
        "reference_point_id": "SYN-RP-OPTIONAL",
        "institutional_signature": {
            "authorization_id": "SYN-AUTH",
            "signature_id": "SYN-SIG",
            "signed_payload_sha256": "b" * 64,
            "verification_status": "NOT_VERIFIED",
        },
    }


def test_full_proposed_fee_contract_is_never_financially_authorized():
    proposal = ProposedAdditionalFeeReference.model_validate(payload())
    assert proposal.unit_price == "10.2500"
    assert proposal.contract_version == 2
    assert proposal.institutional_signature.verification_status == "NOT_VERIFIED"
    assert proposal.financial_authority == "NOT_AUTHORIZED"


@pytest.mark.parametrize("field,value", [
    ("unit_price", "NaN"), ("unit_price", "-1"), ("unit_price", "1.23456"),
    ("unit_price", 10.0), ("currency", "yer"), ("contract_version", 0),
    ("unit", ""), ("fee_code", ""),
])
def test_malformed_values_are_rejected(field, value):
    data = payload()
    data[field] = value
    with pytest.raises(ValidationError):
        ProposedAdditionalFeeReference.model_validate(data)


def test_expired_or_empty_dates_are_rejected():
    data = payload()
    data["effective_until"] = data["effective_from"]
    with pytest.raises(ValidationError):
        ProposedAdditionalFeeReference.model_validate(data)
    data["effective_until"] = date(2025, 1, 1)
    with pytest.raises(ValidationError):
        ProposedAdditionalFeeReference.model_validate(data)


def test_missing_source_and_fake_approval_are_rejected():
    for path, value in [
        (("clause_source", "sha256"), "wrong"),
        (("clause_source", "locator"), ""),
        (("institutional_signature", "verification_status"), "VERIFIED"),
        (("financial_authority",), "AUTHORIZED"),
    ]:
        data = payload()
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        with pytest.raises(ValidationError):
            ProposedAdditionalFeeReference.model_validate(data)


def test_missing_signature_remains_draft_only():
    data = payload()
    data["institutional_signature"] = None
    proposal = ProposedAdditionalFeeReference.model_validate(data)
    assert proposal.review_status == "DRAFT_ONLY"
    assert proposal.financial_authority == "NOT_AUTHORIZED"

def anchor(**changes):
    from mcias.agents.a1_fee_reference_contract import ReadOnlyContractAnchor
    p = payload()
    fields = {name: p[name] for name in (
        "organization_id", "provider_code", "contract_version_id", "contract_version",
        "effective_from", "effective_until", "clause_source")}
    fields["contract_status"] = "approved"
    fields.update(changes)
    return ReadOnlyContractAnchor.model_validate(fields)


def test_read_only_match_remains_unauthorized_even_if_identical():
    from mcias.agents.a1_fee_reference_contract import match_proposed_fee_read_only
    p = ProposedAdditionalFeeReference.model_validate(payload())
    r = match_proposed_fee_read_only(p, anchor(), service_date=date(2026, 6, 1))
    assert r.matching is True and r.reasons == ()
    assert r.signature_verification == "NOT_VERIFIED"
    assert r.financial_authority == "NOT_AUTHORIZED"


@pytest.mark.parametrize("changes,at,reason", [
    ({"provider_code": "OTHER"}, date(2026, 6, 1), "provider_code_mismatch"),
    ({"organization_id": "OTHER"}, date(2026, 6, 1), "organization_id_mismatch"),
    ({"contract_version_id": "OTHER"}, date(2026, 6, 1), "contract_version_id_mismatch"),
    ({"contract_version": 3}, date(2026, 6, 1), "contract_version_mismatch"),
    ({"contract_status": "draft"}, date(2026, 6, 1), "contract_not_approved"),
    ({}, date(2027, 1, 1), "not_effective_on_service_date"),
])
def test_read_only_match_mismatch_and_expiry(changes, at, reason):
    from mcias.agents.a1_fee_reference_contract import match_proposed_fee_read_only
    r = match_proposed_fee_read_only(
        ProposedAdditionalFeeReference.model_validate(payload()), anchor(**changes), service_date=at)
    assert r.matching is False and reason in r.reasons
    assert r.signature_verification == "NOT_VERIFIED"
    assert r.financial_authority == "NOT_AUTHORIZED"


def test_read_only_match_wrong_clause_or_overbroad_fee_period():
    from mcias.agents.a1_fee_reference_contract import match_proposed_fee_read_only
    p = ProposedAdditionalFeeReference.model_validate(payload())
    source = {**payload()["clause_source"], "sha256": "c" * 64}
    r = match_proposed_fee_read_only(p, anchor(clause_source=source), service_date=date(2026, 6, 1))
    assert not r.matching and "clause_source_mismatch" in r.reasons
    r = match_proposed_fee_read_only(
        p, anchor(effective_from=date(2026, 2, 1)), service_date=date(2026, 6, 1))
    assert not r.matching and "fee_period_outside_contract" in r.reasons
