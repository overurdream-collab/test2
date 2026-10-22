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
    certificates.update(_applicable_dataset_certificates(db, claim))
    return [certificates[family] for family, _ in REFERENCE_FAMILIES]

# Source-backed dataset attestations extend the existing G3 registry. A row's
# payload is read from the existing G2 record, never accepted as audit truth from
# a claim request. Approval asserts only the declared tenant/scope/time coverage.
_DATASET_REQUIRED = {
    "beneficiary": {"beneficiary_token": "code", "employee_token": "code", "relationship": "code",
        "category_code": "code", "covered_services": "codes", "eligible": "bool"},
    "contract": {"provider_code": "code", "contract_key": "code", "covered_services": "codes", "excluded_services": "codes"},
    "tariff": {"provider_code": "code", "service_code": "code", "category_code": "code", "currency": "currency",
        "unit": "code", "unit_price": "decimal", "price_basis": "price_basis", "price_comparison": "price_comparison"},
    "policy": {"service_code": "code", "category_code": "code", "currency": "currency", "copay_percent": "percentage",
        "requires_execution_evidence": "bool", "minimum_dispense_interval_days": "nullable_count",
        "copay_basis": "claimed_basis", "rounding": "rounding", "precision": "precision",
        "duplicate_paid_claims_prohibited": "bool"},
    "caps": {"beneficiary_token": "code", "category_code": "code", "service_code": "code", "currency": "currency",
        "limit_amount": "decimal", "consumed_amount": "decimal", "period_from": "date", "period_until": "date",
        "consumption_as_of": "date", "consumed_excludes_current_claim": "bool", "consumption_basis": "claimed_basis"},
    "history": {"beneficiary_token": "code", "provider_code": "code", "service_code": "code", "service_date": "date",
        "claim_reference": "code", "paid": "bool", "quantity": "decimal", "unit": "code", "amount": "decimal", "currency": "currency"},
}
_DATASET_OPTIONAL = {
    "family_token": "code", "dispense_date": "nullable_date", "next_dispense_due_date": "nullable_date",
    "evidence_document_id": "nullable_uuid", "source_claim_reference": "code", "early_dispense_days": "count",
}


def _dataset_value(value, kind):
    import re
    from uuid import UUID
    if kind.startswith("nullable_"):
        return value is None or _dataset_value(value, kind.removeprefix("nullable_"))
    if kind == "bool":
        return type(value) is bool
    if kind == "count":
        return type(value) is int and 0 <= value <= 1000000
    if kind == "code":
        return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value))
    if kind == "codes":
        return isinstance(value, list) and len(value) <= 1000 and all(_dataset_value(v, "code") for v in value) and len(value) == len(set(value))
    if kind == "currency":
        return isinstance(value, str) and bool(re.fullmatch(r"[A-Z]{3}", value))
    if kind == "price_basis":
        return value == "unit_price"
    if kind == "price_comparison":
        return value in ("exact", "ceiling")
    if kind == "claimed_basis":
        return value == "claimed_amount"
    if kind == "rounding":
        return value in ("HALF_UP", "HALF_EVEN")
    if kind == "precision":
        return type(value) is int and value in (0, 2, 4)
    if kind == "uuid":
        try:
            return isinstance(value, str) and str(UUID(value)) == value
        except (ValueError, TypeError):
            return False
    if kind == "date":
        try:
            return isinstance(value, str) and len(value) == 10 and date.fromisoformat(value).isoformat() == value
        except ValueError:
            return False
    if kind in {"decimal", "percentage"}:
        try:
            number = Decimal(value) if isinstance(value, str) else Decimal("NaN")
            return number.is_finite() and 0 <= number < Decimal("100000000000000") and number.as_tuple().exponent >= -4 and (kind != "percentage" or number <= 100)
        except InvalidOperation:
            return False
    return False


def _dataset_payload(family, raw):
    import json
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ReferenceConflict("invalid reference source payload") from exc
    required = {**_DATASET_REQUIRED[family], "effective_from": "date", "effective_until": "date"}
    if (not isinstance(value, dict) or set(required).difference(value)
        or set(value).difference(set(required) | set(_DATASET_OPTIONAL))
        or any(not _dataset_value(value[key], kind) for key, kind in required.items())
        or any(not _dataset_value(value[key], _DATASET_OPTIONAL[key]) for key in set(value) - set(required))):
        raise ReferenceConflict("reference source payload does not satisfy family schema")
    if value["effective_from"] >= value["effective_until"]:
        raise ReferenceConflict("invalid reference row dates")
    if family == "caps" and value["period_from"] >= value["period_until"]:
        raise ReferenceConflict("invalid consumption period")
    if family == "caps" and not value["period_from"] <= value["consumption_as_of"] < value["period_until"]:
        raise ReferenceConflict("consumption timestamp outside source period")
    if family == "history" and Decimal(value["quantity"]) <= 0:
        raise ReferenceConflict("historical quantity must be positive")
    return value


def _dataset_scope(scope):
    # Category is resolved from beneficiary rows by G5; ClaimEntry has no trusted category attribute.
    allowed = {"provider_code", "service_code", "beneficiary_token", "all_providers", "all_services", "all_beneficiaries"}
    if not isinstance(scope, dict) or not scope or set(scope).difference(allowed):
        raise ReferenceConflict("explicit bounded reference scope required")
    for key, value in scope.items():
        if (not _dataset_value(value, "bool" if key.startswith("all_") else "code")
            or (key.startswith("all_") and value is not True)):
            raise ReferenceConflict("invalid reference scope")
    if not any(value is True for key, value in scope.items() if key.startswith("all_")) and not any(not key.startswith("all_") for key in scope):
        raise ReferenceConflict("reference scope does not cover a population")
    return dict(scope)


def _dataset_actor(db, actor, *, approval=False):
    from mcias.models import Role, UserRole
    from mcias.policy import has_permission
    user = db.get(User, getattr(actor, "id", None))
    if user is None or not user.active or not user.organization_id:
        raise ReferenceConflict("active reference organization required")
    permission = has_permission(db, user, "workspace.super_admin")
    if approval:
        role = db.scalar(select(Role.id).join(UserRole, UserRole.role_id == Role.id).where(
            UserRole.user_id == user.id, Role.code == "super_admin"))
        if not role or not permission:
            raise ReferenceConflict("Super Admin reference approval required")
    elif not permission and not has_permission(db, user, "reference.write"):
        raise ReferenceConflict("reference write permission required")
    return user


def _dataset_source(db, item):
    import hashlib
    import json
    import re
    from mcias.models import SourceFile
    from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord, QuarantineItem
    document = db.get(IngestionDocument, item.document_id)
    job = db.get(IngestionJob, item.job_id)
    source = db.get(SourceFile, document.source_id) if document else None
    if (document is None or job is None or source is None
        or document.organization_id != item.organization_id or job.organization_id != item.organization_id
        or job.document_id != document.id or document.status != "extracted" or job.status != "extracted"
        or source.sha256 != document.sha256 or document.sha256 != item.source_sha256
        or not re.fullmatch(r"[0-9a-f]{64}", source.sha256 or "")
        or not isinstance(job.manifest, dict) or job.manifest.get("complete") is not True
        or job.manifest.get("quarantined_units") != 0
        or job.manifest.get("format") not in {"csv", "xlsx"}
        or db.scalar(select(QuarantineItem.id).where(QuarantineItem.job_id == job.id))):
        raise ReferenceConflict("reference source unavailable or incomplete")
    if (job.manifest.get("expected_units") != item.expected_record_count
        or job.manifest.get("processed_units") != item.expected_record_count):
        raise ReferenceConflict("reference source control total mismatch")
    records = db.scalars(select(ExtractedSourceRecord).where(ExtractedSourceRecord.job_id == job.id)
        .order_by(ExtractedSourceRecord.id)).all()
    if len(records) != item.expected_record_count or not records:
        raise ReferenceConflict("reference source control total mismatch")
    keys, typed = set(), []
    for record in records:
        if (record.confidence != 100 or not isinstance(record.values, dict)
            or not isinstance(record.locator, dict) or set(record.values) != {"record_key", "payload"}
            or not _dataset_value(record.values.get("record_key"), "code")
            or record.values["record_key"] in keys or record.locator.get("kind") not in {"row", "sheet"}
            or type(record.locator.get("row")) is not int or record.locator["row"] < 2):
            raise ReferenceConflict("reference source row is ambiguous or unqualified")
        keys.add(record.values["record_key"])
        value = _dataset_payload(item.family, record.values["payload"])
        linked = value.get("evidence_document_id")
        if linked:
            evidence = db.get(IngestionDocument, linked)
            if evidence is None or evidence.organization_id != item.organization_id or evidence.status != "extracted":
                raise ReferenceConflict("reference evidence is not tenant scoped")
        typed.append({"source_record_id": record.id, "record_key": record.values["record_key"],
            "locator": dict(record.locator), "values": value})
    material = {"document_id": document.id, "job_id": job.id, "sha256": source.sha256,
        "manifest": job.manifest, "records": [{"id": record.id, "locator": record.locator,
            "values": record.values, "confidence": record.confidence} for record in records]}
    fingerprint = hashlib.sha256(json.dumps(material, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode()).hexdigest()
    return fingerprint, typed, source


def register_reference_dataset(db, actor, document_id, family, *, dataset_key, version,
        effective_from, effective_until, coverage_from, coverage_until, scope,
        expected_record_count, owner_organization_id=None):
    from mcias.models_reference import ReferenceDatasetVersion
    from mcias.models_ingestion import IngestionDocument, IngestionJob
    user = _dataset_actor(db, actor)
    if (family not in _DATASET_REQUIRED or not _dataset_value(dataset_key, "code") or len(dataset_key) > 100
        or type(version) is not int or version < 1 or type(expected_record_count) is not int or expected_record_count < 1
        or not all(type(day) is date for day in (effective_from, effective_until, coverage_from, coverage_until))
        or effective_from >= effective_until or coverage_from >= coverage_until
        or owner_organization_id not in {None, user.organization_id}):
        raise ReferenceConflict("invalid reference dataset definition")
    document = db.get(IngestionDocument, document_id)
    if document is None or document.organization_id != user.organization_id:
        raise ReferenceConflict("reference document not accessible")
    job = db.scalar(select(IngestionJob).where(IngestionJob.document_id == document.id,
        IngestionJob.organization_id == user.organization_id).order_by(IngestionJob.created_at.desc(), IngestionJob.id.desc()))
    if job is None:
        raise ReferenceConflict("reference extraction job missing")
    item = ReferenceDatasetVersion(organization_id=user.organization_id, owner_organization_id=user.organization_id,
        family=family, dataset_key=dataset_key, version=version, document_id=document.id, job_id=job.id,
        source_sha256=document.sha256, source_fingerprint="", effective_from=effective_from,
        effective_until=effective_until, coverage_from=coverage_from, coverage_until=coverage_until,
        scope=_dataset_scope(scope), expected_record_count=expected_record_count, status="draft", created_by=user.id)
    fingerprint, _, _ = _dataset_source(db, item)
    item.source_fingerprint = fingerprint
    db.add(item)
    db.flush()
    from mcias.audit_writer import write_event
    write_event(db, actor=user, organization_id=user.organization_id, action="reference_dataset_registered",
        resource_type="reference_dataset_version", resource_id=item.id, outcome="success",
        details={"version": item.version, "status": "draft", "effective_from": effective_from.isoformat(),
                 "effective_until": effective_until.isoformat()})
    db.commit()
    return item


def approve_reference_dataset(db, actor, dataset_id, *, reason_code):
    from mcias.models import now_utc
    from mcias.models_reference import ReferenceDatasetVersion
    from mcias.audit_writer import write_event
    user = _dataset_actor(db, actor, approval=True)
    item = db.scalar(select(ReferenceDatasetVersion).where(ReferenceDatasetVersion.id == dataset_id,
        ReferenceDatasetVersion.organization_id == user.organization_id).with_for_update())
    if item is None:
        raise ReferenceConflict("reference dataset not accessible")
    if reason_code != "source_scope_complete":
        raise ReferenceConflict("explicit source scope completeness attestation required")
    fingerprint, _, _ = _dataset_source(db, item)
    if fingerprint != item.source_fingerprint:
        raise ReferenceConflict("reference source changed after registration")
    if item.status == "approved":
        return item
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import text
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": "reference_dataset:" + item.organization_id + ":" + item.family + ":" + item.dataset_key})
    overlap = db.scalar(select(ReferenceDatasetVersion.id).where(
        ReferenceDatasetVersion.organization_id == item.organization_id,
        ReferenceDatasetVersion.family == item.family, ReferenceDatasetVersion.dataset_key == item.dataset_key,
        ReferenceDatasetVersion.status == "approved", ReferenceDatasetVersion.id != item.id,
        ReferenceDatasetVersion.effective_from < item.effective_until,
        ReferenceDatasetVersion.effective_until > item.effective_from))
    if overlap:
        raise ReferenceConflict("approved reference dataset periods overlap")
    approval = write_event(db, actor=user, organization_id=user.organization_id, action="reference_dataset_approved",
        resource_type="reference_dataset_version", resource_id=item.id, outcome="success",
        details={"version": item.version, "status": "approved", "effective_from": item.effective_from.isoformat(),
                 "effective_until": item.effective_until.isoformat()})
    item.approved_by, item.approved_at, item.approval_event_id = user.id, now_utc(), approval.id
    item.status = "approved"
    db.commit()
    return item


def _scope_matches_claim(scope, claim):
    return all(key.startswith("all_") or getattr(claim, key, None) == value for key, value in scope.items())


def _applicable_dataset_certificates(db, claim):
    from mcias.models_reference import ReferenceDatasetVersion
    # Legacy callers may run against migrations before this additive table.
    # They retain legacy incomplete certificates rather than gaining authority.
    from sqlalchemy import inspect
    connection = db.connection()
    schema = (connection.get_execution_options().get("schema_translate_map") or {}).get(None)
    if not inspect(connection).has_table(ReferenceDatasetVersion.__tablename__, schema=schema):
        return {}
    rows = db.scalars(select(ReferenceDatasetVersion).where(
        ReferenceDatasetVersion.organization_id == claim.organization_id)).all()
    results = {}
    for family, _ in REFERENCE_FAMILIES:
        candidates = [item for item in rows if item.family == family and _scope_matches_claim(item.scope, claim)]
        if not candidates:
            continue
        dated = [item for item in candidates if item.effective_from <= claim.service_date < item.effective_until
                 and item.coverage_from <= claim.service_date < item.coverage_until]
        approved = [item for item in dated if item.status == "approved"]
        certificate = _reference_certificate(family, claim.organization_id, claim.service_date, "reference_dataset_version",
            owner_organization_id=claim.organization_id, gaps=["reference_missing"])
        if len(approved) != 1:
            status = "reference_conflict" if len(approved) > 1 else "reference_unapproved" if dated else "reference_not_effective"
            certificate.update(lookup_status=status, gaps=[status])
            results[family] = certificate
            continue
        item = approved[0]
        certificate.update(reference_id=item.id, dataset_id=item.id, version=item.version,
            effective_from=item.effective_from.isoformat(), effective_until=item.effective_until.isoformat(),
            coverage_from=item.coverage_from.isoformat(), coverage_until=item.coverage_until.isoformat(),
            owner_organization_id=item.owner_organization_id, scope=dict(item.scope),
            approval_event_id=item.approval_event_id, approved_by=item.approved_by,
            completeness_basis="SUPER_ADMIN_SOURCE_SCOPE_ATTESTATION", expected_record_count=item.expected_record_count)
        try:
            fingerprint, records, source = _dataset_source(db, item)
            approval = db.get(AuditLog, item.approval_event_id)
            approver = db.get(User, item.approved_by)
            if (fingerprint != item.source_fingerprint or approval is None
                or approval.actor_id != item.approved_by or approval.action != "reference_dataset_approved"
                or approval.resource_id != item.id or approval.resource_type != "reference_dataset_version"
                or approval.details.get("organization_id") != item.organization_id
                or approval.details.get("outcome") != "success" or approver is None
                or approver.organization_id != item.organization_id):
                raise ReferenceConflict("reference approval or source changed")
        except ReferenceConflict:
            certificate.update(lookup_status="reference_incomplete", gaps=["source_hash_invalid"])
        else:
            applicable = [record for record in records if date.fromisoformat(record["values"]["effective_from"]) <= claim.service_date
                          < date.fromisoformat(record["values"]["effective_until"])]
            certificate.update(approved=True, complete=True, lookup_complete=True, lookup_status="reference_applicable",
                gaps=[], records=applicable, source_fingerprint=fingerprint,
                source_evidence=[{"source_id": source.id, "document_id": item.document_id,
                    "source_sha256": source.sha256, "approval_event_id": item.approval_event_id}],
                observed_record_count=len(records))
        results[family] = certificate
    return results
