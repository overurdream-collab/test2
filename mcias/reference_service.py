"""G3 reference lifecycle: draft revisions, tariffs, enrollments and auditable approvals."""
from datetime import date
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from mcias.models import AuditLog, WrittenAuthorization, User
from mcias.models_reference import ContractVersion, ProviderTariff, BeneficiaryCategory, BeneficiaryEnrollment
from mcias.reference import ReferenceConflict, check_contract_overlap, analyze_retroactive, validate_enrollment, reference_fingerprint

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
                           precedence=precedence, status="draft", created_by=actor.id)
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
    if contract.created_by == actor.id:
        raise ReferenceConflict("proposal author cannot review own impact")
    result = analyze_retroactive(db, contract, as_of or date.today())
    _audit(db, actor, "contract_impact_reviewed", "contract_version", contract.id,
           {"rationale": rationale.strip(), "impact": result, "reviewer_id": actor.id,
            "fingerprint": reference_fingerprint(contract)})
    db.commit()
    return result

def approve_precedence_policy(db, actor, contract_id, rationale):
    contract = db.get(ContractVersion, contract_id, with_for_update=True)
    if contract is None:
        raise ReferenceConflict("contract unavailable")
    _tenant(actor, contract.organization_id)
    if contract.status != "draft" or not rationale or len(rationale.strip()) < 20:
        raise ReferenceConflict("substantive precedence rationale required")
    if contract.created_by == actor.id:
        raise ReferenceConflict("proposal author cannot approve own precedence")
    if not contract.authorization_id:
        raise ReferenceConflict("written authorization required before precedence review")
    auth = db.get(WrittenAuthorization, contract.authorization_id)
    if auth is None or auth.approved_by == actor.id:
        raise ReferenceConflict("precedence reviewer must be independent of written approver")
    _audit(db, actor, "contract_precedence_approved", "contract_version", contract.id,
           {"rationale": rationale.strip(), "precedence": contract.precedence,
            "fingerprint": reference_fingerprint(contract)})
    db.commit()
    return {"contract_id": contract.id, "precedence_reviewed": True}

def apply_tariff_batch(db, actor, contract_id, rows):
    contract = db.get(ContractVersion, contract_id, with_for_update=True)
    if contract is None:
        raise ReferenceConflict("contract unavailable")
    _tenant(actor, contract.organization_id)
    if contract.status != "draft":
        raise ReferenceConflict("tariff import requires draft contract")
    existing = set(db.scalars(select(ProviderTariff.service_code).where(
        ProviderTariff.contract_id == contract_id)).all())
    codes = [row["service_code"] for row in rows]
    if len(codes) != len(set(codes)) or existing.intersection(codes):
        raise ReferenceConflict("duplicate service code in tariff batch")
    for row in rows:
        db.add(ProviderTariff(contract_id=contract_id, service_code=row["service_code"],
                              amount=Decimal(row["amount"]), currency=row["currency"]))
    db.flush()
    _audit(db, actor, "tariff_batch_imported", "contract_version", contract_id,
           {"count": len(rows)})
    db.commit()
    return {"contract_id": contract_id, "imported": len(rows)}

# These six families are the owner's binding INPUTS-FIRST directive, not an
# inferred list of the database tables that happen to exist today. See
# docs/CAI01_EXCEL_TO_G4_SOURCE_CONTRACT_AR.md, section 9.
REFERENCE_FAMILIES = (
    ("beneficiary", "beneficiary identity, employee/family membership, per-person class/coverage and dates"),
    ("contract", "approved contracts and provider terms/exclusions"),
    ("tariff", "provider/contract/class/date-specific tariffs"),
    ("policy", "medical, administrative and financial policies/authorization"),
    ("caps", "benefit caps and cumulative consumption"),
    ("history", "historical claims/dispensing and recurrence/chronic medication context"),
)


def _reference_certificate(family, organization_id, at, reference_type, **values):
    certificate = {
        "family": family,
        "label": dict(REFERENCE_FAMILIES)[family],
        "reference_type": reference_type,
        "reference_id": None,
        "version": None,
        "organization_id": organization_id,
        "service_date": at.isoformat(),
        "effective_from": None,
        "effective_until": None,
        "approved": False,
        "complete": False,
        # Completeness of a bounded native lookup is distinct from completeness
        # of the whole required family. G5 must retain that scope distinction.
        "lookup_complete": False,
        "lookup_status": "reference_missing",
        "source_evidence": [],
        "gaps": [],
    }
    certificate.update(values)
    return certificate


def _written_reference_evidence(db, organization_id, authorization_id, contract):
    """Resolve bounded evidence without copying source text or patient values."""
    import re
    from mcias.models import SourceFile
    if not authorization_id:
        return False, [], ["authorization_missing"]
    authorization = db.get(WrittenAuthorization, authorization_id)
    approver = db.get(User, authorization.approved_by) if authorization else None
    if (authorization is None or authorization.organization_id != organization_id
            or approver is None or approver.organization_id != organization_id):
        return False, [], ["authorization_invalid"]
    source = db.get(SourceFile, authorization.source_id)
    if source is None:
        return False, [], ["source_missing"]
    if not re.fullmatch(r"[0-9a-f]{64}", source.sha256 or ""):
        return False, [], ["source_hash_invalid"]
    from mcias.production_authorization import verify_production_approval
    if not verify_production_approval(db, contract, authorization):
        return False, [], ["authorization_invalid"]
    return True, [{"source_id": source.id, "source_sha256": source.sha256,
                   "authorization_id": authorization.id}], []


def applicable_reference_snapshots(db, claim, policy=None):
    """Read six dated, tenant-scoped certificates from the existing references.

    This is an evidence projection, never an approval or absence certificate.
    In particular an empty/incomplete enrollment or usage source cannot prove
    ineligibility, no prior consumption, or fraud. Missing schema dimensions
    remain explicit gaps rather than synthetic authoritative reference rows.
    No data is written and the caller's transaction is not committed.
    """
    from mcias.models_claims import ClaimEntry
    from mcias.models_audit_policy import AuditPolicyGrant

    org, at = claim.organization_id, claim.service_date
    if not org or not isinstance(at, date):
        raise ReferenceConflict("organization and service date required")
    certificates = {}

    enrollments = db.scalars(select(BeneficiaryEnrollment).where(
        BeneficiaryEnrollment.organization_id == org,
        BeneficiaryEnrollment.beneficiary_token == claim.beneficiary_token,
        BeneficiaryEnrollment.effective_from <= at,
        BeneficiaryEnrollment.effective_until > at)).all()
    beneficiary = _reference_certificate("beneficiary", org, at, "beneficiary_enrollment",
        gaps=["beneficiary_approval_missing", "beneficiary_version_missing",
              "family_membership_unavailable", "coverage_history_unavailable"])
    if len(enrollments) == 1:
        enrollment = enrollments[0]
        category = db.get(BeneficiaryCategory, enrollment.category_id)
        if category is not None and category.organization_id == org:
            beneficiary.update(reference_id=enrollment.id,
                effective_from=enrollment.effective_from.isoformat(),
                effective_until=enrollment.effective_until.isoformat(),
                lookup_status="reference_incomplete")
        else:
            beneficiary["gaps"].append("reference_conflict")
            beneficiary["lookup_status"] = "reference_conflict"
    elif len(enrollments) > 1:
        beneficiary["lookup_status"] = "reference_conflict"
        beneficiary["gaps"].append("reference_conflict")
    else:
        beneficiary["gaps"].append("reference_missing")
    certificates["beneficiary"] = beneficiary

    # Date filtering precedes any version selection. A newer version that is
    # effective later can never replace the historical service-date version.
    contracts = db.scalars(select(ContractVersion).where(
        ContractVersion.organization_id == org,
        ContractVersion.provider_code == claim.provider_code)).all()
    dated = [item for item in contracts if item.effective_from <= at < item.effective_until]
    approved = [item for item in dated if item.status == "approved"]
    contract = approved[0] if len(approved) == 1 else None
    contract_certificate = _reference_certificate("contract", org, at, "contract_version",
        scope="native_contract_version", gaps=["contract_terms_unavailable"])
    if len(approved) > 1:
        contract_certificate["lookup_status"] = "reference_conflict"
        contract_certificate["gaps"].append("reference_conflict")
    elif contract is not None:
        authorized, evidence, gaps = _written_reference_evidence(db, org, contract.authorization_id, contract)
        contract_certificate.update(reference_id=contract.id, version=contract.version,
            effective_from=contract.effective_from.isoformat(),
            effective_until=contract.effective_until.isoformat(), approved=authorized,
            lookup_complete=authorized, source_evidence=evidence,
            lookup_status="reference_applicable" if authorized else "reference_unapproved")
        contract_certificate["gaps"].extend(gaps)
    else:
        status = "reference_unapproved" if dated else "reference_not_effective" if contracts else "reference_missing"
        contract_certificate["lookup_status"] = status
        contract_certificate["gaps"].append(status)
    certificates["contract"] = contract_certificate

    tariff_certificate = _reference_certificate("tariff", org, at, "provider_tariff",
        scope="native_contract_service", gaps=["tariff_class_scope_unavailable"])
    tariff = db.scalar(select(ProviderTariff).where(
        ProviderTariff.contract_id == contract.id,
        ProviderTariff.service_code == claim.service_code)) if contract else None
    if tariff is not None:
        tariff_certificate.update(reference_id=tariff.id, version=contract.version,
            contract_id=contract.id, effective_from=contract.effective_from.isoformat(),
            effective_until=contract.effective_until.isoformat(),
            approved=contract_certificate["approved"],
            source_evidence=list(contract_certificate["source_evidence"]))
        if tariff.currency == claim.currency and contract_certificate["lookup_complete"]:
            tariff_certificate.update(lookup_status="reference_applicable", lookup_complete=True)
        else:
            tariff_certificate["lookup_status"] = ("reference_conflict" if tariff.currency != claim.currency
                                                      else "reference_unapproved")
            tariff_certificate["gaps"].append(tariff_certificate["lookup_status"])
    else:
        tariff_certificate["gaps"].append("reference_missing")
    certificates["tariff"] = tariff_certificate

    policy_certificate = _reference_certificate("policy", org, at, "audit_policy_grant",
        scope="native_policy_grant", gaps=["policy_effective_dates_unavailable", "policy_source_unavailable"])
    # A grant is evidence of policy authorization, not of a service-date range
    # or of medical/administrative policy completeness. Verify its signature
    # using the existing registry before describing even that bounded approval.
    grant = None
    if policy is not None:
        from mcias.audit_service import fingerprint_policy
        from mcias.audit_policy_registry import resolve_grant
        from mcias.audit_engine import PolicyBlocked
        try:
            fingerprint = fingerprint_policy(policy)
            grant = db.scalar(select(AuditPolicyGrant).where(
                AuditPolicyGrant.organization_id == org,
                AuditPolicyGrant.policy_id == policy.policy_id,
                AuditPolicyGrant.policy_fingerprint == fingerprint,
                AuditPolicyGrant.revoked_at.is_(None)))
            if grant is not None:
                resolve_grant(db, organization_id=org, policy_fingerprint=fingerprint,
                              policy_id=policy.policy_id)
                policy_certificate.update(reference_id=grant.id, approved=True, lookup_complete=True,
                    lookup_status="reference_incomplete", content_sha256=fingerprint)
        except (PolicyBlocked, ValueError, TypeError, AttributeError):
            policy_certificate["lookup_status"] = "reference_unapproved"
            policy_certificate["gaps"].append("reference_unapproved")
    if grant is None:
        policy_certificate["gaps"].append("reference_missing")
    certificates["policy"] = policy_certificate

    certificates["caps"] = _reference_certificate("caps", org, at, "audit_policy_grant",
        reference_id=policy_certificate["reference_id"], approved=policy_certificate["approved"],
        lookup_status="reference_incomplete" if policy_certificate["reference_id"] else "reference_missing",
        gaps=["cap_consumption_unavailable", "policy_effective_dates_unavailable"])

    history = db.scalars(select(ClaimEntry).where(
        ClaimEntry.organization_id == org,
        ClaimEntry.beneficiary_token == claim.beneficiary_token,
        ClaimEntry.service_date < at).order_by(ClaimEntry.service_date, ClaimEntry.id).limit(100)).all()
    certificates["history"] = _reference_certificate("history", org, at, "claim_entry",
        lookup_status="reference_incomplete",
        # Existing rows are a bounded observation, never a complete dispensing
        # or clinical history. Original values and identifiers stay protected.
        observed_record_ids=[item.id for item in history],
        gaps=["historical_source_incomplete", "dispensing_context_unavailable"])
    return [certificates[family] for family, _ in REFERENCE_FAMILIES]
