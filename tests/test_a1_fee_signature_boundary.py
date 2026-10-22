"""Synthetic fee signature boundary regression; not authorization of fee references."""
from datetime import date
from hashlib import sha256
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mcias.authorization_signatures import verify_written_authorization
from mcias.agents.a1_fee_reference_contract import (
    ProposedAdditionalFeeReference, ReadOnlyContractAnchor,
    match_proposed_fee_read_only,
)


def _proposal():
    return ProposedAdditionalFeeReference.model_validate({
        "organization_id": "SYN-ORG", "provider_code": "SYN-H1",
        "contract_version_id": "SYN-CV", "contract_version": 3,
        "fee_code": "SYN-FEE", "unit": "invoice", "unit_price": "7.00",
        "currency": "YER", "effective_from": date(2026, 1, 1),
        "effective_until": date(2027, 1, 1),
        "clause_source": {"document_id": "SYN-DOC", "sha256": "a"*64,
                          "locator": "pdf:page:1:line:7"},
    })


def _anchor(p):
    return ReadOnlyContractAnchor.model_validate({
        "organization_id": p.organization_id, "provider_code": p.provider_code,
        "contract_version_id": p.contract_version_id,
        "contract_version": p.contract_version,
        "contract_status": "approved", "effective_from": p.effective_from,
        "effective_until": p.effective_until, "clause_source": p.clause_source,
    })


def test_existing_ed25519_primitive_fails_closed_on_missing_and_changed_fee_payload():
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes_raw()
    payload = b"SYN|org|contract-v3|fee-code|source-hash|expiry=2027-01-01"
    digest = sha256(payload).hexdigest()
    signature = key.sign(payload).hex()
    assert verify_written_authorization(payload, digest, signature, public)
    assert not verify_written_authorization(payload, digest, "", public)
    assert not verify_written_authorization(payload.replace(b"contract-v3", b"contract-v4"),
                                            digest, signature, public)
    assert not verify_written_authorization(payload.replace(b"source-hash", b"other-hash"),
                                            digest, signature, public)


def test_expired_signature_claim_and_structural_match_cannot_authorize():
    p = _proposal()
    a = _anchor(p)
    for at in (date(2026, 6, 1), date(2027, 1, 1)):
        result = match_proposed_fee_read_only(p, a, service_date=at)
        assert result.signature_verification == "NOT_VERIFIED"
        assert result.financial_authority == "NOT_AUTHORIZED"
        assert result.matching == (at == date(2026, 6, 1))


def test_supplied_signature_metadata_never_becomes_trusted():
    d = _proposal().model_dump()
    d["institutional_signature"] = {
        "authorization_id": "SYN-AUTH", "signature_id": "SYN-SIG",
        "signed_payload_sha256": "b"*64, "verification_status": "NOT_VERIFIED",
    }
    p = ProposedAdditionalFeeReference.model_validate(d)
    result = match_proposed_fee_read_only(p, _anchor(p), service_date=date(2026, 6, 1))
    assert result.matching
    assert result.signature_verification == "NOT_VERIFIED"
    assert result.financial_authority == "NOT_AUTHORIZED"
