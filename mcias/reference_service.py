"""G3 reference lifecycle: draft revisions, tariffs, enrollments and auditable approvals."""
from datetime import date
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from mcias.models import AuditLog, WrittenAuthorization, User
from mcias.models_reference import ContractVersion, ProviderTariff, BeneficiaryCategory, BeneficiaryEnrollment
from mcias.reference import ReferenceConflict, check_contract_overlap, analyze_retroactive, validate_enrollment

def _audit(db, actor, action, kind, resource_id, details=None):
    db.add(AuditLog(actor_id=actor.id, action=action, resource_type=kind,
                    resource_id=resource_id, details=details or {}))

def _tenant(actor, organization_id):
    if not actor.active or actor.organization_id != organization_id:
        raise ReferenceConflict("organization access denied")

def create_draft(db, actor, provider_code, start, end, precedence=0):
    _tenant(actor, actor.organization_id)
    if not provider_code or len(provider_code) > 80 or start >= end or precedence < 0:
        raise ReferenceConflict("invalid contract draft")
    # Serialise allocation of the next version per organization/provider.
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                   {"key": actor.organization_id + ":" + provider_code})
    current = db.scalar(select(__import__("sqlalchemy").func.max(ContractVersion.version)).where(
        ContractVersion.organization_id == actor.organization_id,
        ContractVersion.provider_code == provider_code)) or 0
    item = ContractVersion(organization_id=actor.organization_id, provider_code=provider_code,
                           version=current + 1, effective_from=start, effective_until=end,
                           precedence=precedence, status="draft")
    db.add(item); db.flush()
    _audit(db, actor, "contract_draft_created", "contract_version", item.id,
           {"version": item.version, "provider_code": provider_code})
    db.commit()
    return item

def add_tariff(db, actor, contract_id, service_code, amount, currency):
    contract = db.get(ContractVersion, contract_id, with_for_update=True)
    if contract is None:
        raise ReferenceConflict("contract unavailable")
    _tenant(actor, contract.organization_id)
    if contract.status != "draft":
        raise ReferenceConflict("approved tariff is immutable")
    if not service_code or len(service_code) > 100 or len(currency) != 3 or not currency.isalpha() or currency != currency.upper():
        raise ReferenceConflict("invalid tariff code/currency")
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        raise ReferenceConflict("invalid tariff amount")
    if not value.is_finite() or value < 0 or value.as_tuple().exponent < -4 or value >= Decimal("100000000000000"):
        raise ReferenceConflict("invalid tariff precision or range")
    if db.scalar(select(ProviderTariff.id).where(ProviderTariff.contract_id == contract_id,
                                                  ProviderTariff.service_code == service_code)):
        raise ReferenceConflict("duplicate service code in contract")
    item = ProviderTariff(contract_id=contract_id, service_code=service_code, amount=value, currency=currency)
    db.add(item); db.flush()
    _audit(db, actor, "tariff_added", "provider_tariff", item.id, {"contract_id": contract_id})
    db.commit()
    return item

def create_category(db, actor, code, description):
    if not actor.organization_id or not code or len(code) > 80 or not description or len(description) > 200:
        raise ReferenceConflict("invalid category")
    item = BeneficiaryCategory(organization_id=actor.organization_id, code=code, description=description)
    db.add(item); db.flush()
    _audit(db, actor, "beneficiary_category_created", "beneficiary_category", item.id)
    db.commit()
    return item

def enroll(db, actor, token, category_id, start, end):
    if not actor.organization_id or not token or len(token) > 128 or start >= end:
        raise ReferenceConflict("invalid enrollment")
    item = BeneficiaryEnrollment(organization_id=actor.organization_id, beneficiary_token=token,
                                 category_id=category_id, effective_from=start, effective_until=end)
    validate_enrollment(db, item)
    db.add(item); db.flush()
    _audit(db, actor, "beneficiary_enrolled", "beneficiary_enrollment", item.id,
           {"category_id": category_id, "effective_from": start.isoformat(), "effective_until": end.isoformat()})
    db.commit()
    return item

def eligibility(db, organization_id, token, at):
    matches = db.scalars(select(BeneficiaryEnrollment).where(
        BeneficiaryEnrollment.organization_id == organization_id,
        BeneficiaryEnrollment.beneficiary_token == token,
        BeneficiaryEnrollment.effective_from <= at,
        BeneficiaryEnrollment.effective_until > at)).all()
    if len(matches) > 1:
        raise ReferenceConflict("ambiguous beneficiary enrollment")
    return matches[0] if matches else None

def attach_authorization(db, actor, contract_id, authorization_id):
    contract = db.get(ContractVersion, contract_id, with_for_update=True)
    if contract is None:
        raise ReferenceConflict("contract unavailable")
    _tenant(actor, contract.organization_id)
    if contract.status != "draft":
        raise ReferenceConflict("contract not draft")
    authorization = db.get(WrittenAuthorization, authorization_id)
    approver = db.get(User, authorization.approved_by) if authorization else None
    if (not authorization or authorization.organization_id != contract.organization_id
        or authorization.approved_by == actor.id or not approver or not approver.active
        or approver.organization_id != contract.organization_id):
        raise ReferenceConflict("independent same-tenant written authorization required")
    contract.authorization_id = authorization_id
    _audit(db, actor, "contract_authorization_attached", "contract_version", contract.id,
           {"authorization_id": authorization_id})
    db.commit()
    return contract

def impact_review(db, actor, contract_id, rationale, as_of=None):
    contract = db.get(ContractVersion, contract_id, with_for_update=True)
    if contract is None:
        raise ReferenceConflict("contract unavailable")
    _tenant(actor, contract.organization_id)
    if contract.status != "draft" or not rationale or len(rationale.strip()) < 20:
        raise ReferenceConflict("draft and substantive review rationale required")
    result = analyze_retroactive(db, contract, as_of or date.today())
    _audit(db, actor, "contract_impact_reviewed", "contract_version", contract.id,
           {"rationale": rationale.strip(), "impact": result, "reviewer_id": actor.id})
    db.commit()
    return result
