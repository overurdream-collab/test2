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


def inspect_claim(db,claim:ClaimEntry,policy=None,*,actor=None,review_only=False):
    if review_only:
        return _inspect_inputs_first_review(db, claim, actor)
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


# Official INPUTS-FIRST vocabulary for the current review contract. Historical
# immutable snapshots retain their original values; only this read projection
# translates them, with an explicit version marker.
AUDIT_STATE_SCHEMA_VERSION = 2
OFFICIAL_AUDIT_STATES = frozenset({"MATCH_VERIFIED", "VIOLATION_PROVEN", "UNRESOLVED", "AUDIT_UNAVAILABLE"})
_LEGACY_AUDIT_STATES = {"VERIFIED_MATCH": "MATCH_VERIFIED", "PROVEN_VIOLATION": "VIOLATION_PROVEN",
    "UNRESOLVED_OR_MISSING_REFERENCE": "UNRESOLVED", "AUDIT_NOT_POSSIBLE": "AUDIT_UNAVAILABLE"}


def canonical_audit_state(value):
    if value in OFFICIAL_AUDIT_STATES:
        return value
    if value in _LEGACY_AUDIT_STATES:
        return _LEGACY_AUDIT_STATES[value]
    raise ValueError("unknown audit state")


def project_audit_findings(findings):
    """Return the official read contract without changing historical JSON."""
    from copy import deepcopy
    result = deepcopy(findings)
    result.setdefault("source_audit_state_schema_version", result.get("audit_state_schema_version", 1))
    result["audit_state"] = canonical_audit_state(result.get("audit_state"))
    result["audit_state_schema_version"] = AUDIT_STATE_SCHEMA_VERSION
    for finding in result.get("agents", []):
        if "audit_state" in finding:
            finding["audit_state"] = canonical_audit_state(finding["audit_state"])
    certificates = result.get("reference_certificates")
    if result["audit_state"] == "UNRESOLVED" and isinstance(certificates, list) and any(
        isinstance(certificate, dict) and (certificate.get("complete") is False or certificate.get("gaps"))
        for certificate in certificates
    ):
        result.setdefault("reason_code", "REFERENCE_INCOMPLETE")
    return result


def _review_number(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if (not number.is_finite() or number < 0 or (positive and number == 0)
        or number >= Decimal("100000000000000") or number.as_tuple().exponent < -4):
        return None
    return number


def _record_values(record):
    return record.get("values", {}) if isinstance(record, dict) else {}


def _certificate_ready(certificate, claim):
    from datetime import date
    try:
        return bool(certificate.get("dataset_id") and certificate.get("approved") is True
            and certificate.get("complete") is True and certificate.get("lookup_status") == "reference_applicable"
            and certificate.get("organization_id") == claim.organization_id
            and date.fromisoformat(certificate["effective_from"]) <= claim.service_date < date.fromisoformat(certificate["effective_until"])
            and date.fromisoformat(certificate["coverage_from"]) <= claim.service_date < date.fromisoformat(certificate["coverage_until"])
            and certificate.get("source_evidence") and not certificate.get("gaps")
            and isinstance(certificate.get("records"), list))
    except (KeyError, TypeError, ValueError):
        return False


def _matching_records(certificate, **identity):
    return [record for record in certificate.get("records", [])
        if all(_record_values(record).get(key) == value for key, value in identity.items())]


def _execution_evidence(db, claim, quantity, unit):
    """Bound native G2 rows to this claim; OCR/page text is not field attestation."""
    attachments = db.scalars(select(ClaimAttachment).where(
        ClaimAttachment.organization_id == claim.organization_id, ClaimAttachment.claim_id == claim.id)).all()
    evidence_ids, issues = [], []
    for attachment in attachments:
        document = db.get(IngestionDocument, attachment.ingestion_document_id)
        source = db.get(SourceFile, document.source_id) if document else None
        if (document is None or source is None or document.organization_id != claim.organization_id
            or document.status != "extracted" or source.sha256 != document.sha256
            or document.sha256 != attachment.document_sha256):
            issues.append("attachment_source_unavailable")
            continue
        from mcias.models_ingestion import IngestionJob
        jobs = db.scalars(select(IngestionJob).where(IngestionJob.document_id == document.id,
            IngestionJob.organization_id == claim.organization_id).order_by(IngestionJob.created_at.desc(), IngestionJob.id)).all()
        if not jobs or jobs[0].status != "extracted" or not jobs[0].manifest.get("complete"):
            issues.append("attachment_extraction_incomplete")
            continue
        records = db.scalars(select(ExtractedSourceRecord).where(ExtractedSourceRecord.job_id == jobs[0].id)).all()
        for record in records:
            values, locator = record.values, record.locator
            if values.get("claim_reference") != claim.claim_reference:
                continue
            if record.confidence != 100 or locator.get("kind") not in {"row", "sheet"}:
                issues.append("field_locator_unqualified")
                continue
            if type(locator.get("row")) is not int or locator["row"] < 2:
                issues.append("field_locator_unqualified")
                continue
            if values.get("dose_status") == "ambiguous":
                issues.append("dose_ambiguous")
            if values.get("evidence_kind") == "prescription":
                if (values.get("service_code") != claim.service_code or
                    (values.get("quantity") and _review_number(values["quantity"]) != quantity)):
                    issues.append("invoice_prescription_conflict")
                continue
            if values.get("evidence_kind") != "service_execution":
                continue
            if (values.get("beneficiary_token") != claim.beneficiary_token
                or values.get("provider_code") != claim.provider_code
                or values.get("service_code") != claim.service_code
                or values.get("service_date") != claim.service_date.isoformat()
                or values.get("unit") != unit
                or _review_number(values.get("performed_quantity"), positive=True) != quantity):
                issues.append("execution_identity_or_quantity_conflict")
                continue
            evidence_ids.append(record.id)
    return sorted(set(evidence_ids)), sorted(set(issues))


def _inspect_inputs_first_review(db, claim, actor):
    """Existing advisory agents with approved source-backed G3 dataset facts."""
    from datetime import date, timedelta
    from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP
    from mcias.reference_service import applicable_reference_snapshots
    certificates = applicable_reference_snapshots(db, claim, None)
    refs = {item["family"]: item for item in certificates}
    source = _claim_source(db, claim, actor)
    findings = []

    def ready(*families):
        return all(_certificate_ready(refs.get(family, {}), claim) for family in families)

    def add(agent, state, reason, families, records=()):
        findings.append({"agent": agent, "status": "pass" if state == "MATCH_VERIFIED" else "review" if state == "VIOLATION_PROVEN" else "hold",
            "audit_state": state, "reason": reason, "rule_id": agent, "rule_version": 2,
            "reference_families": list(families),
            "reference": [record["source_record_id"] for record in records if record.get("source_record_id")]})

    beneficiaries = _matching_records(refs.get("beneficiary", {}), beneficiary_token=claim.beneficiary_token) if ready("beneficiary") else []
    beneficiary = _record_values(beneficiaries[0]) if len(beneficiaries) == 1 else {}
    category = beneficiary.get("category_code")
    if len(beneficiaries) == 1 and type(beneficiary.get("eligible")) is bool:
        eligible = beneficiary["eligible"] and claim.service_code in beneficiary.get("covered_services", [])
        add("eligibility", "MATCH_VERIFIED" if eligible else "VIOLATION_PROVEN", "dated_beneficiary_coverage", ("beneficiary",), beneficiaries)
    elif ready("beneficiary") and not beneficiaries and refs["beneficiary"].get("scope", {}).get("all_beneficiaries") is True:
        add("eligibility", "VIOLATION_PROVEN", "absent_from_attested_complete_population", ("beneficiary",))
    else:
        add("eligibility", "UNRESOLVED", "beneficiary_reference_incomplete_or_ambiguous", ("beneficiary",))

    contracts = _matching_records(refs.get("contract", {}), provider_code=claim.provider_code) if ready("contract") else []
    contract = _record_values(contracts[0]) if len(contracts) == 1 else {}
    if contract:
        excluded = claim.service_code in contract.get("excluded_services", [])
        covered = claim.service_code in contract.get("covered_services", [])
        add("contract", "MATCH_VERIFIED" if covered or excluded else "VIOLATION_PROVEN", "dated_contract_service_scope", ("contract",), contracts)
    else:
        add("contract", "UNRESOLVED", "contract_reference_incomplete_or_ambiguous", ("contract",))

    quantity = _review_number(claim.source_values.get("quantity"), positive=True)
    unit_price = _review_number(claim.source_values.get("unit_price"))
    unit = claim.source_values.get("unit")
    tariffs = _matching_records(refs.get("tariff", {}), provider_code=claim.provider_code,
        service_code=claim.service_code, category_code=category, currency=claim.currency, unit=unit) if ready("tariff", "beneficiary", "contract") else []
    tariff = _record_values(tariffs[0]) if len(tariffs) == 1 else {}
    reference_price = _review_number(tariff.get("unit_price"))
    if (source and quantity is not None and unit_price is not None and reference_price is not None
        and tariff.get("price_basis") == "unit_price" and quantity * unit_price == claim.claimed_amount
        and tariff.get("price_comparison") in {"exact", "ceiling"}):
        price_matches = unit_price == reference_price if tariff["price_comparison"] == "exact" else unit_price <= reference_price
        add("tariff", "MATCH_VERIFIED" if price_matches else "VIOLATION_PROVEN",
            "explicit_contract_unit_price_comparison", ("beneficiary", "contract", "tariff"), tariffs)
    else:
        add("tariff", "UNRESOLVED", "unit_price_authority_or_quantity_incomplete", ("beneficiary", "contract", "tariff"))

    policies = _matching_records(refs.get("policy", {}), service_code=claim.service_code,
        category_code=category, currency=claim.currency) if ready("policy", "beneficiary") else []
    policy = _record_values(policies[0]) if len(policies) == 1 else {}
    if contract and policy:
        add("exclusion", "VIOLATION_PROVEN" if claim.service_code in contract.get("excluded_services", []) else "MATCH_VERIFIED",
            "explicit_dated_contract_exclusion", ("contract", "policy"), contracts + policies)
    else:
        add("exclusion", "UNRESOLVED", "dated_exclusion_policy_incomplete", ("contract", "policy"))

    caps = _matching_records(refs.get("caps", {}), beneficiary_token=claim.beneficiary_token,
        category_code=category, service_code=claim.service_code, currency=claim.currency) if ready("caps", "policy", "beneficiary") else []
    cap = _record_values(caps[0]) if len(caps) == 1 else {}
    limit, consumed = _review_number(cap.get("limit_amount")), _review_number(cap.get("consumed_amount"))
    try:
        dated_cap = date.fromisoformat(cap["period_from"]) <= claim.service_date < date.fromisoformat(cap["period_until"])
    except (KeyError, TypeError, ValueError):
        dated_cap = False
    if (source and policy and limit is not None and consumed is not None and dated_cap
        and cap.get("consumption_as_of") == claim.service_date.isoformat()
        and cap.get("consumed_excludes_current_claim") is True and cap.get("consumption_basis") == "claimed_amount"):
        # The attested summary is the entire consumption input. Never add
        # historical rows again or double-count this claim in that summary.
        add("caps", "VIOLATION_PROVEN" if consumed + claim.claimed_amount > limit else "MATCH_VERIFIED",
            "attested_consumption_plus_current_claim", ("beneficiary", "policy", "caps"), caps)
    else:
        add("caps", "UNRESOLVED", "cap_basis_or_consumption_incomplete", ("beneficiary", "policy", "caps"))

    copay = _review_number(claim.source_values.get("copay_amount"))
    percent = _review_number(policy.get("copay_percent"))
    rounding = {"HALF_UP": ROUND_HALF_UP, "HALF_EVEN": ROUND_HALF_EVEN}.get(policy.get("rounding"))
    precision = policy.get("precision")
    if (source and policy and ready("contract") and policy.get("copay_basis") == "claimed_amount" and percent is not None
        and percent <= 100 and copay is not None and type(precision) is int and precision in (0, 2, 4) and rounding is not None):
        expected = (claim.claimed_amount * percent / Decimal(100)).quantize(Decimal(1).scaleb(-precision), rounding=rounding)
        add("cost_sharing", "MATCH_VERIFIED" if copay == expected else "VIOLATION_PROVEN",
            "explicit_dated_cost_sharing", ("beneficiary", "contract", "policy"), policies)
        findings[-1]["expected_amount"] = str(expected)
    else:
        add("cost_sharing", "UNRESOLVED", "cost_sharing_basis_or_observation_incomplete", ("beneficiary", "contract", "policy"))

    history = []
    for row in refs.get("history", {}).get("records", []) if ready("history") else []:
        try:
            if date.fromisoformat(_record_values(row)["service_date"]) <= claim.service_date:
                history.append(row)
        except (KeyError, TypeError, ValueError):
            continue
    same_reference = [row for row in history if _record_values(row).get("claim_reference") == claim.claim_reference]
    same_claim = [row for row in same_reference if (
        _record_values(row).get("beneficiary_token") == claim.beneficiary_token
        and _record_values(row).get("provider_code") == claim.provider_code
        and _record_values(row).get("service_code") == claim.service_code
        and _record_values(row).get("service_date") == claim.service_date.isoformat()
        and _record_values(row).get("paid") is True
        and _record_values(row).get("unit") == unit
        and _record_values(row).get("currency") == claim.currency
        and _review_number(_record_values(row).get("quantity"), positive=True) == quantity
        and _review_number(_record_values(row).get("amount")) == claim.claimed_amount)]
    native_duplicates = db.scalars(select(ClaimEntry.id).where(ClaimEntry.organization_id == claim.organization_id,
        ClaimEntry.claim_reference == claim.claim_reference, ClaimEntry.id != claim.id)).all()
    early, missing_schedule = False, False
    periodic_rows = []
    for row in history:
        item = _record_values(row)
        if (item.get("beneficiary_token") != claim.beneficiary_token or item.get("service_code") != claim.service_code
            or item.get("provider_code") != claim.provider_code):
            continue
        periodic_rows.append(row)
        if not item.get("next_dispense_due_date"):
            # A clinical service date alone does not establish when medication
            # was dispensed or when a further supply becomes due.
            interval = policy.get("minimum_dispense_interval_days")
            if interval is not None and (type(interval) is not int or interval > 0):
                missing_schedule = True
            continue
        try:
            allowed = policy.get("early_dispense_days", 0)
            if type(allowed) is not int or allowed < 0:
                early = True
            elif claim.service_date < date.fromisoformat(item["next_dispense_due_date"]) - timedelta(days=allowed):
                early = True
        except (TypeError, ValueError):
            early = True
    if ready("history", "policy") and same_claim and policy.get("duplicate_paid_claims_prohibited") is True:
        add("duplicates", "VIOLATION_PROVEN", "exact_paid_claim_in_attested_history", ("history", "policy"), same_claim)
    elif ready("history", "policy") and not native_duplicates and not same_reference and not early and not missing_schedule:
        add("duplicates", "MATCH_VERIFIED", "no_duplicate_in_attested_scope_periodic_use_allowed", ("history", "policy"), history)
    else:
        review_rows = {row["source_record_id"]: row for row in same_reference + periodic_rows}
        add("duplicates", "UNRESOLVED", "dispensing_schedule_incomplete" if missing_schedule else
            "duplicate_or_early_dispense_requires_review", ("history", "policy"),
            [review_rows[key] for key in sorted(review_rows)])

    execution_ids, evidence_issues = _execution_evidence(db, claim, quantity, unit)
    if source is None:
        add("evidence", "AUDIT_UNAVAILABLE", "source_unavailable", ())
    elif evidence_issues or (policy.get("requires_execution_evidence") is not False and not execution_ids):
        add("evidence", "UNRESOLVED", evidence_issues[0] if evidence_issues else "execution_evidence_missing", ())
    elif not policy:
        add("evidence", "UNRESOLVED", "evidence_policy_incomplete", ("policy",))
    else:
        add("evidence", "MATCH_VERIFIED", "source_and_required_execution_evidence", ("policy",))
    findings[-1]["reference"] = execution_ids
    assert tuple(item["agent"] for item in findings) == AGENTS
    if source is None:
        # Invalid claim provenance cannot support even a check-local proof.
        for finding in findings:
            if finding["audit_state"] in {"MATCH_VERIFIED", "VIOLATION_PROVEN"}:
                finding.update(audit_state="UNRESOLVED", status="hold", reason="claim_source_unavailable")
    states = {finding["audit_state"] for finding in findings}
    all_references = len(refs) == 6 and all(_certificate_ready(value, claim) for value in refs.values())
    if "AUDIT_UNAVAILABLE" in states:
        state, reason = "AUDIT_UNAVAILABLE", "SOURCE_UNAVAILABLE"
    elif not all_references:
        state, reason = "UNRESOLVED", "REFERENCE_INCOMPLETE"
    elif "UNRESOLVED" in states:
        state, reason = "UNRESOLVED", "EVIDENCE_INCOMPLETE"
    elif "VIOLATION_PROVEN" in states:
        state, reason = "VIOLATION_PROVEN", "PROVEN_RULE_BREACH"
    else:
        state, reason = "MATCH_VERIFIED", "CHECKS_COMPLETED"
    executed = sum(finding["audit_state"] in {"MATCH_VERIFIED", "VIOLATION_PROVEN"} for finding in findings)
    return {"findings": findings, "audit_state": state, "audit_state_schema_version": 2,
        "reason_code": reason, "reference_certificates": certificates, "source_evidence": source,
        "coverage": {"required": len(AGENTS), "executed": executed, "blocked": len(AGENTS) - executed},
        "review_required": state != "MATCH_VERIFIED", "evidence_complete": source is not None and not evidence_issues
            and (bool(execution_ids) or policy.get("requires_execution_evidence") is False)}
