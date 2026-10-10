"""Eight specialized *advisory* checks, with explicit provenance and no AI verdict."""
from decimal import Decimal
from sqlalchemy import select
from mcias.models_reference import BeneficiaryEnrollment, ProviderTariff
from mcias.models_claims import ClaimAttachment, ClaimEntry
from mcias.reference import active_contract

AGENTS=("eligibility","tariff","contract","exclusion","caps","cost_sharing","duplicates","evidence")

def inspect_claim(db,claim:ClaimEntry,policy):
    findings=[]
    def add(agent,status,reason,reference=None):
        findings.append({"agent":agent,"status":status,"reason":reason,"reference":reference})
    enrollment=db.scalars(select(BeneficiaryEnrollment).where(
        BeneficiaryEnrollment.organization_id==claim.organization_id,
        BeneficiaryEnrollment.beneficiary_token==claim.beneficiary_token,
        BeneficiaryEnrollment.effective_from<=claim.service_date,
        BeneficiaryEnrollment.effective_until>claim.service_date)).all()
    add("eligibility","pass" if len(enrollment)==1 else "hold",
        "active enrollment" if len(enrollment)==1 else "missing or ambiguous enrollment",
        enrollment[0].id if len(enrollment)==1 else None)
    contract=active_contract(db,claim.organization_id,claim.provider_code,claim.service_date)
    add("contract","pass" if contract else "hold",
        "approved active contract" if contract else "no approved contract",contract.id if contract else None)
    tariff=db.scalar(select(ProviderTariff).where(ProviderTariff.contract_id==contract.id,
        ProviderTariff.service_code==claim.service_code)) if contract else None
    tariff_ok=tariff is not None and tariff.currency==claim.currency
    add("tariff","pass" if tariff_ok else "hold","approved matching tariff" if tariff_ok else "tariff missing or currency mismatch",
        tariff.id if tariff_ok else None)
    add("exclusion","pass" if policy.approved else "hold","policy-backed exclusion" if policy.approved else "unapproved policy",policy.policy_id)
    add("caps","pass" if policy.approved else "hold","policy-backed cap" if policy.approved else "unapproved policy",policy.policy_id)
    add("cost_sharing","pass" if policy.approved else "hold","policy-backed cost sharing" if policy.approved else "unapproved policy",policy.policy_id)
    duplicates=db.scalars(select(ClaimEntry.id).where(ClaimEntry.organization_id==claim.organization_id,
        ClaimEntry.claim_reference==claim.claim_reference,ClaimEntry.id!=claim.id)).all()
    add("duplicates","review" if duplicates else "pass","possible repeated reference" if duplicates else "unique reference",
        duplicates[:10] if duplicates else None)
    attachments=db.scalars(select(ClaimAttachment.id).where(
        ClaimAttachment.organization_id==claim.organization_id,ClaimAttachment.claim_id==claim.id)).all()
    add("evidence","pass" if attachments else "hold","attachment linked" if attachments else "no linked evidence",
        attachments)
    assert tuple(x["agent"] for x in findings)==AGENTS
    return {"findings":findings,"contract":contract,"tariff":tariff if tariff_ok else None,
            "enrollment":enrollment[0] if len(enrollment)==1 else None,
            "eligible":len(enrollment)==1,"evidence_complete":bool(attachments),
            "review_required":bool(duplicates) or any(x["status"]=="hold" for x in findings)}
