"""Temporal reference controls. All effective ranges are half-open [start, end)."""
from datetime import date
from sqlalchemy import select
from mcias.models import AuditLog, WrittenAuthorization
from mcias.models_reference import ContractVersion, ProviderTariff, BeneficiaryEnrollment

class ReferenceConflict(ValueError):
    pass

def overlaps(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    if a_start >= a_end or b_start >= b_end:
        raise ReferenceConflict("invalid effective period")
    return a_start < b_end and b_start < a_end

def check_contract_overlap(db, contract: ContractVersion):
    existing = db.scalars(select(ContractVersion).where(
        ContractVersion.organization_id == contract.organization_id,
        ContractVersion.provider_code == contract.provider_code,
        ContractVersion.status == "approved",
        ContractVersion.id != contract.id,
        ContractVersion.effective_from < contract.effective_until,
        ContractVersion.effective_until > contract.effective_from)).all()
    if existing:
        raise ReferenceConflict("T04 conflicting approved contract effective dates")

def analyze_retroactive(db, contract: ContractVersion, as_of: date) -> dict:
    prior = db.scalars(select(ContractVersion).where(
        ContractVersion.organization_id == contract.organization_id,
        ContractVersion.provider_code == contract.provider_code,
        ContractVersion.status == "approved",
        ContractVersion.effective_from < contract.effective_until,
        ContractVersion.effective_until > contract.effective_from)).all()
    affected = [x.id for x in prior if x.id != contract.id]
    return {"retroactive": contract.effective_from < as_of,
            "conflicting_contract_ids": affected,
            "requires_human_review": contract.effective_from < as_of or bool(affected),
            "financial_impact": "not_calculated_without_approved_claims_engine"}

def approve_contract(db, contract_id: str, actor, as_of: date, *, precedence_approved: bool = False):
    contract = db.get(ContractVersion, contract_id, with_for_update=True)
    if contract is None or contract.organization_id != actor.organization_id:
        raise ReferenceConflict("contract not accessible")
    if contract.status != "draft":
        raise ReferenceConflict("only draft contract may be approved")
    if not precedence_approved:
        raise ReferenceConflict("contract precedence decision is required")
    authorization = db.get(WrittenAuthorization, contract.authorization_id) if contract.authorization_id else None
    if authorization is None or authorization.organization_id != contract.organization_id or authorization.approved_by == actor.id:
        raise ReferenceConflict("independent written authorization required")
    check_contract_overlap(db, contract)
    impact = analyze_retroactive(db, contract, as_of)
    if impact["requires_human_review"]:
        raise ReferenceConflict("T05 retroactive or conflicting contract requires documented impact review")
    contract.status = "approved"
    db.add(AuditLog(actor_id=actor.id, action="contract_approved", resource_type="contract_version",
                    resource_id=contract.id, details={"authorization_id": authorization.id, "impact": impact}))
    db.commit()
    return {"id": contract.id, "status": "approved"}

def active_contract(db, organization_id: str, provider_code: str, at: date):
    contracts = db.scalars(select(ContractVersion).where(
        ContractVersion.organization_id == organization_id,
        ContractVersion.provider_code == provider_code,
        ContractVersion.status == "approved",
        ContractVersion.effective_from <= at,
        ContractVersion.effective_until > at)).all()
    if len(contracts) > 1:
        raise ReferenceConflict("conflicting active contracts")
    return contracts[0] if contracts else None

def validate_enrollment(db, enrollment: BeneficiaryEnrollment):
    from mcias.models_reference import BeneficiaryCategory
    category = db.get(BeneficiaryCategory, enrollment.category_id)
    if category is None or category.organization_id != enrollment.organization_id:
        raise ReferenceConflict("beneficiary category must belong to same organization")
    if enrollment.effective_from >= enrollment.effective_until:
        raise ReferenceConflict("invalid enrollment period")
    conflict = db.scalars(select(BeneficiaryEnrollment).where(
        BeneficiaryEnrollment.organization_id == enrollment.organization_id,
        BeneficiaryEnrollment.beneficiary_token == enrollment.beneficiary_token,
        BeneficiaryEnrollment.id != enrollment.id,
        BeneficiaryEnrollment.effective_from < enrollment.effective_until,
        BeneficiaryEnrollment.effective_until > enrollment.effective_from)).first()
    if conflict:
        raise ReferenceConflict("overlapping beneficiary enrollment")
