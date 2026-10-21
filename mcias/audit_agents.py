"""Eight evidence-bound advisory checks; a finding never authorizes payment."""
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from mcias.models_reference import BeneficiaryEnrollment, ProviderTariff
from mcias.models_claims import ClaimAttachment, ClaimBatch, ClaimEntry
from mcias.models_ingestion import ExtractedSourceRecord, IngestionDocument
from mcias.models import SourceFile, User
from mcias.reference import active_contract, ReferenceConflict

AGENTS=("eligibility","contract","tariff","exclusion","caps","cost_sharing","duplicates","evidence")


def _claim_source(db, claim, actor):
    """Revalidate the approved G2/G4 ledger, not caller-provided locator text."""
    from mcias.claim_batches import BatchConflict, source_scope
    from mcias.claim_normalization import normalize, ClaimValidationError
    batch=db.get(ClaimBatch,claim.batch_id)
    if batch is None or batch.organization_id!=claim.organization_id:
        return None
    document=db.get(IngestionDocument,batch.ingestion_document_id)
    source=db.get(SourceFile,document.source_id) if document else None
    record=db.get(ExtractedSourceRecord,claim.extracted_record_id)
    actor=actor or db.get(User,batch.created_by)
    if (document is None or source is None or record is None or actor is None
        or document.organization_id!=claim.organization_id
        or batch.source_sha256!=document.sha256 or source.sha256!=document.sha256
        or record.values!=claim.source_values or record.confidence!=100):
        return None
    try:
        normalized=normalize(record.values)
        if any(getattr(claim,key)!=value for key,value in normalized.items()):
            return None
        scope=source_scope(db,actor,document.id)
    except (BatchConflict,ClaimValidationError):
        return None
    locator=claim.source_locator
    if (record.id not in scope["eligible_record_ids"]
        or any(locator.get(key)!=value for key,value in record.locator.items())
        or locator.get("sheet_type")!="CLAIMS"
        or locator.get("document_id")!=document.id
        or locator.get("job_id")!=record.job_id
        or locator.get("source_sha256")!=document.sha256
        or locator.get("source_scope_approval_id")!=scope["approval_id"]
        or locator.get("mapping_version")!=scope["mapping_version"]):
        return None
    return {"source_record_id":record.id,"document_id":document.id,
            "source_sha256":document.sha256,"source_scope_approval_id":scope["approval_id"]}


def inspect_claim(db,claim:ClaimEntry,policy,*,actor=None):
    from mcias.reference_service import applicable_reference_snapshots
    certificates=applicable_reference_snapshots(db,claim,policy)
    refs={item["family"]:item for item in certificates}
    source_evidence=_claim_source(db,claim,actor)
    findings=[]

    def ready(*families):
        return all(refs[name]["approved"] and refs[name]["complete"]
                   and refs[name]["lookup_status"]=="reference_applicable" for name in families)

    def add(agent,status,reason,reference=None,*,state=None,families=()):
        state=state or ("VERIFIED_MATCH" if status=="pass" else "UNRESOLVED_OR_MISSING_REFERENCE")
        findings.append({"agent":agent,"status":status,"reason":reason,"reference":reference,
            "audit_state":state,"reference_families":list(families),
            "rule_id":agent,"rule_version":1})

    enrollment=db.scalars(select(BeneficiaryEnrollment).where(
        BeneficiaryEnrollment.organization_id==claim.organization_id,
        BeneficiaryEnrollment.beneficiary_token==claim.beneficiary_token,
        BeneficiaryEnrollment.effective_from<=claim.service_date,
        BeneficiaryEnrollment.effective_until>claim.service_date)).all()
    enrollment_ok=len(enrollment)==1 and ready("beneficiary")
    add("eligibility","pass" if enrollment_ok else "hold",
        "approved dated beneficiary reference" if enrollment_ok else "beneficiary reference incomplete or unavailable",
        enrollment[0].id if len(enrollment)==1 else None,families=("beneficiary",))
    try:
        contract=active_contract(db,claim.organization_id,claim.provider_code,claim.service_date)
    except ReferenceConflict:
        contract=None
    contract_ok=contract is not None and ready("contract")
    add("contract","pass" if contract_ok else "hold",
        "approved dated contract terms" if contract_ok else "contract terms incomplete or unavailable",
        contract.id if contract else None,families=("contract",))
    tariff=db.scalar(select(ProviderTariff).where(ProviderTariff.contract_id==contract.id,
        ProviderTariff.service_code==claim.service_code)) if contract else None
    tariff_ok=tariff is not None and tariff.currency==claim.currency
    # The native tariff has a narrower, explicitly certified contract/service
    # scope. It can prove this comparison while class coverage remains unresolved.
    tariff_ref=refs["tariff"]
    policy_ref=refs["policy"]
    tariff_proven=(tariff_ok and source_evidence is not None
        and tariff_ref["approved"] and tariff_ref.get("lookup_complete",False)
        and bool(tariff_ref["source_evidence"]) and policy_ref["approved"]
        and policy_ref.get("lookup_complete",False)
        and getattr(policy,"currency",None)==claim.currency
        and getattr(policy,"tariff",None)==tariff.amount)
    if tariff_proven:
        try:
            amount=Decimal(str(claim.claimed_amount))
            tariff_proven=amount.is_finite() and amount>=0
        except (InvalidOperation,ValueError,TypeError):
            tariff_proven=False
    if tariff_proven:
        exceeded=amount>tariff.amount
        add("tariff","review" if exceeded else "pass",
            "native contract service tariff exceeded" if exceeded else "within native contract service tariff",
            tariff.id,state="PROVEN_VIOLATION" if exceeded else "VERIFIED_MATCH",families=("contract","tariff","policy"))
        findings[-1].update({"scope":"native_contract_service","observed_value":str(amount),
            "reference_value":str(tariff.amount),"currency":claim.currency})
    else:
        add("tariff","hold","approved dated tariff, policy or source evidence unavailable",
            tariff.id if tariff_ok else None,families=("contract","tariff","policy"))
    exclusion_ok=ready("contract","policy")
    add("exclusion","pass" if exclusion_ok else "hold",
        "approved dated exclusion evidence" if exclusion_ok else "exclusion evidence incomplete",
        getattr(policy,"policy_id",None),families=("contract","policy"))
    caps_ok=ready("caps","policy")
    add("caps","pass" if caps_ok else "hold",
        "approved cap and complete consumption evidence" if caps_ok else "cap or cumulative consumption evidence incomplete",
        getattr(policy,"policy_id",None),families=("caps","policy"))
    sharing_ok=ready("beneficiary","contract","policy")
    add("cost_sharing","pass" if sharing_ok else "hold",
        "approved dated cost sharing evidence" if sharing_ok else "dated class and cost sharing evidence incomplete",
        getattr(policy,"policy_id",None),families=("beneficiary","contract","policy"))
    duplicates=db.scalars(select(ClaimEntry.id).where(ClaimEntry.organization_id==claim.organization_id,
        ClaimEntry.claim_reference==claim.claim_reference,ClaimEntry.id!=claim.id)).all()
    duplicate_ok=not duplicates and ready("history")
    add("duplicates","review" if duplicates else "pass" if duplicate_ok else "hold",
        "possible repeated reference" if duplicates else "complete history without repeated reference" if duplicate_ok
        else "historical source completeness unavailable",duplicates[:10] if duplicates else None,families=("history",))
    attachments=db.scalars(select(ClaimAttachment).where(
        ClaimAttachment.organization_id==claim.organization_id,ClaimAttachment.claim_id==claim.id)).all()
    valid_attachments=[]
    for attachment in attachments:
        document=db.get(IngestionDocument,attachment.ingestion_document_id)
        source=db.get(SourceFile,document.source_id) if document else None
        if (document and source and document.organization_id==claim.organization_id
            and source.sha256==document.sha256==attachment.document_sha256
            and document.status in ("extracted","review_required")):
            valid_attachments.append(attachment.id)
    evidence_complete=bool(valid_attachments) and source_evidence is not None
    add("evidence","pass" if evidence_complete else "hold",
        "source ledger and attachment verified" if evidence_complete else "source ledger or linked evidence unavailable",
        valid_attachments,state=("AUDIT_NOT_POSSIBLE" if source_evidence is None else None))
    assert tuple(x["agent"] for x in findings)==AGENTS
    states={item["audit_state"] for item in findings}
    # An individual proven discrepancy is retained even when another mandatory
    # check is blocked. The overall claim may never be presented as fully audited.
    audit_state=next((value for value in ("AUDIT_NOT_POSSIBLE","UNRESOLVED_OR_MISSING_REFERENCE",
        "PROVEN_VIOLATION","VERIFIED_MATCH") if value in states),"AUDIT_NOT_POSSIBLE")
    completed=sum(item["audit_state"] in ("VERIFIED_MATCH","PROVEN_VIOLATION") for item in findings)
    return {"findings":findings,"contract":contract,"tariff":tariff if tariff_ok else None,
            "enrollment":enrollment[0] if len(enrollment)==1 else None,
            "eligible":enrollment_ok,"evidence_complete":evidence_complete,
            "review_required":audit_state!="VERIFIED_MATCH","audit_state":audit_state,
            "reference_certificates":certificates,"source_evidence":source_evidence,
            "coverage":{"required":len(AGENTS),"executed":completed,"blocked":len(AGENTS)-completed}}
