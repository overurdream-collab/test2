"""Proposed A1 fee-reference data contract, never an active financial rule.

This immutable structure describes a *candidate* cross-branch mapping. Validating
shape or a supplied signature reference NEVER verifies a signature or grants authority.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class FeeSource(Strict):
    document_id: str = Field(min_length=1, max_length=128)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    locator: str = Field(min_length=1, max_length=256)


class InstitutionalSignatureReference(Strict):
    """Unverified signature metadata; verification requires institutional services."""
    authorization_id: str = Field(min_length=1, max_length=128)
    signature_id: str = Field(min_length=1, max_length=128)
    signed_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verification_status: Literal["NOT_VERIFIED"] = "NOT_VERIFIED"


class ProposedAdditionalFeeReference(Strict):
    schema_version: Literal["mcias.a1.fee_reference.proposal.v1"] = "mcias.a1.fee_reference.proposal.v1"
    organization_id: str = Field(min_length=1, max_length=128)
    provider_code: str = Field(min_length=1, max_length=80)
    contract_version_id: str = Field(min_length=1, max_length=128)
    contract_version: int = Field(ge=1)
    fee_code: str = Field(min_length=1, max_length=100)
    unit: str = Field(min_length=1, max_length=80)
    unit_price: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    effective_from: date
    effective_until: date
    clause_source: FeeSource
    reference_point_id: str | None = Field(default=None, min_length=1, max_length=128)
    institutional_signature: InstitutionalSignatureReference | None = None
    review_status: Literal["DRAFT_ONLY", "HUMAN_REVIEWED_NOT_AUTHORIZED"] = "DRAFT_ONLY"
    financial_authority: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"

    @field_validator("unit_price")
    @classmethod
    def validate_price(cls, value):
        if type(value) is not str:
            raise ValueError("unit price must be an exact decimal string")
        try:
            n = Decimal(value)
        except InvalidOperation:
            raise ValueError("invalid decimal") from None
        if (not n.is_finite() or n < 0 or n >= Decimal("100000000000000")
                or n.as_tuple().exponent < -4):
            raise ValueError("invalid amount or precision")
        return format(n, "f")

    @model_validator(mode="after")
    def validate_period(self):
        if self.effective_from >= self.effective_until:
            raise ValueError("fee validity must use a nonempty half-open interval")
        return self

class ReadOnlyContractAnchor(Strict):
    organization_id: str = Field(min_length=1)
    provider_code: str = Field(min_length=1)
    contract_version_id: str = Field(min_length=1)
    contract_version: int = Field(ge=1)
    contract_status: Literal["approved", "draft"]
    effective_from: date
    effective_until: date
    clause_source: FeeSource


class FeeMatchResult(Strict):
    matching: bool
    reasons: tuple[str, ...]
    signature_verification: Literal["NOT_VERIFIED"] = "NOT_VERIFIED"
    financial_authority: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"


def match_proposed_fee_read_only(proposal: ProposedAdditionalFeeReference,
                                 anchor: ReadOnlyContractAnchor, *, service_date: date) -> FeeMatchResult:
    """Structural comparison, not cryptographic or financial authorization."""
    reasons = []
    for name in ("organization_id", "provider_code", "contract_version_id", "contract_version"):
        if getattr(proposal, name) != getattr(anchor, name):
            reasons.append(name + "_mismatch")
    if anchor.contract_status != "approved":
        reasons.append("contract_not_approved")
    if not (anchor.effective_from <= service_date < anchor.effective_until
            and proposal.effective_from <= service_date < proposal.effective_until):
        reasons.append("not_effective_on_service_date")
    if proposal.effective_from < anchor.effective_from or proposal.effective_until > anchor.effective_until:
        reasons.append("fee_period_outside_contract")
    if proposal.clause_source != anchor.clause_source:
        reasons.append("clause_source_mismatch")
    return FeeMatchResult(matching=not reasons, reasons=tuple(reasons))
