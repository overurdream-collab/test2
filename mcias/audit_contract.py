"""Bounded audit metadata validation. Phase 2A: no schema change."""
import re
from uuid import UUID, uuid4

_CODE = re.compile(r"^[a-z][a-z0-9_]{0,119}$", re.ASCII)
_RESOURCE = re.compile(r"^[a-z][a-z0-9_]{0,89}$", re.ASCII)
_OPAQUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,35}$", re.ASCII)
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$", re.ASCII)
_REASON = frozenset({"permission_denied", "tenant_or_permission_denied", "reference_conflict",
                     "revision_rejected", "invalid_request", "operation_failed"})
_STATUS = frozenset({"draft", "active", "approved", "rejected", "denied", "error",
                     "success", "superseded", "pending", "inactive"})
_OUTCOMES = frozenset({"success", "denied", "error"})
_METADATA = frozenset({"version", "previous_version", "previous_id", "new_id",
                       "effective_from", "effective_until", "reason_code",
                       "contract_number", "status"})

def validate_event(action, resource_type, resource_id, outcome):
    if not isinstance(action, str) or not _CODE.fullmatch(action):
        raise ValueError("invalid audit action")
    if not isinstance(resource_type, str) or not _RESOURCE.fullmatch(resource_type):
        raise ValueError("invalid audit resource type")
    if resource_id is not None and (not isinstance(resource_id, str) or not _OPAQUE.fullmatch(resource_id)):
        raise ValueError("invalid audit resource id")
    if outcome not in _OUTCOMES:
        raise ValueError("invalid audit outcome")

def clean_details(details):
    if not isinstance(details, dict):
        return {}
    result = {}
    for key, value in details.items():
        if key not in _METADATA:
            continue
        if key in {"version", "previous_version"}:
            if type(value) is int and 0 <= value <= 999999999:
                result[key] = value
        elif key in {"previous_id", "new_id"}:
            if isinstance(value, str) and _OPAQUE.fullmatch(value):
                result[key] = value
        elif key in {"effective_from", "effective_until"}:
            if isinstance(value, str) and _DATE.fullmatch(value):
                from datetime import date
                try:
                    date.fromisoformat(value)
                except ValueError:
                    continue
                result[key] = value
        elif key == "reason_code" and isinstance(value, str) and value in _REASON:
            result[key] = value
        elif key == "status" and isinstance(value, str) and value in _STATUS:
            result[key] = value
        elif key == "contract_number":
            # Unverified business-origin values may contain PHI; fail closed.
            # This optional field is intentionally omitted pending classification.
            continue
    return result

def new_request_attempt_id():
    """Create one new opaque server-generated ID per invocation/HTTP attempt.

    Not stored; no database deduplication or request middleware in Phase 2A.
    """
    return str(uuid4())


# The claim-audit event carries bounded references, never claim values or text.
CLAIM_AUDIT_ACTION = "claim_inputs_audited"
CLAIM_AUDIT_STATES = frozenset({"VERIFIED_MATCH", "PROVEN_VIOLATION",
    "UNRESOLVED_OR_MISSING_REFERENCE", "AUDIT_NOT_POSSIBLE"})
REFERENCE_FAMILIES = frozenset({"beneficiary", "contract", "tariff", "policy", "caps", "history"})
REFERENCE_STATUSES = frozenset({"reference_applicable", "reference_missing", "reference_unapproved",
    "reference_not_effective", "reference_conflict", "reference_incomplete"})
REFERENCE_GAPS = frozenset({"reference_missing", "reference_unapproved", "reference_not_effective",
    "reference_conflict", "authorization_missing", "authorization_invalid", "source_missing",
    "source_hash_invalid", "beneficiary_approval_missing", "beneficiary_version_missing",
    "family_membership_unavailable", "coverage_history_unavailable", "contract_terms_unavailable",
    "tariff_class_scope_unavailable", "policy_effective_dates_unavailable", "policy_source_unavailable",
    "cap_consumption_unavailable", "historical_source_incomplete", "dispensing_context_unavailable"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


def _uuid(value):
    if not isinstance(value, str):
        raise ValueError("audit correlation must be a UUID")
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ValueError("audit correlation must be a UUID") from exc
    if str(parsed) != value:
        raise ValueError("audit correlation must be a canonical UUID")
    return value


def clean_claim_audit_details(details):
    """Validate the coordinated G3/G5 contract; exclude all untyped metadata.

    Malformed required correlation fails closed. Unrecognized optional data is
    discarded, including raw source values, personal identifiers and narratives.
    """
    if not isinstance(details, dict):
        raise ValueError("claim audit correlation required")
    result = {key: _uuid(details.get(key)) for key in (
        "audit_snapshot_id", "source_record_id", "document_id")}
    for key in ("source_sha256", "policy_fingerprint"):
        value = details.get(key)
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise ValueError("claim audit SHA-256 required")
        result[key] = value
    if details.get("audit_state") not in CLAIM_AUDIT_STATES:
        raise ValueError("invalid claim audit state")
    result["audit_state"] = details["audit_state"]
    if "policy_version" in details:
        value = details["policy_version"]
        if type(value) is not int or not 1 <= value <= 999999999:
            raise ValueError("invalid claim audit policy version")
        result["policy_version"] = value
    references = details.get("references")
    if not isinstance(references, list) or len(references) != len(REFERENCE_FAMILIES):
        raise ValueError("six reference certificates required")
    seen = set()
    safe_references = []
    for reference in references:
        if not isinstance(reference, dict):
            raise ValueError("invalid reference certificate")
        family, status = reference.get("family"), reference.get("status")
        if family not in REFERENCE_FAMILIES or family in seen or status not in REFERENCE_STATUSES:
            raise ValueError("invalid reference certificate family or status")
        seen.add(family)
        reference_id, version = reference.get("id"), reference.get("version")
        if reference_id is not None:
            reference_id = _uuid(reference_id)
        if version is not None and (type(version) is not int or not 1 <= version <= 999999999):
            raise ValueError("invalid reference certificate version")
        if status == "reference_applicable" and (reference_id is None or version is None):
            raise ValueError("applicable reference requires identity and version")
        evidence = reference.get("evidence_ids")
        gaps = reference.get("gaps")
        if not isinstance(evidence, list) or len(evidence) > 64:
            raise ValueError("invalid reference evidence")
        if not isinstance(gaps, list) or len(gaps) > len(REFERENCE_GAPS):
            raise ValueError("invalid reference gaps")
        if any(not isinstance(gap, str) or gap not in REFERENCE_GAPS for gap in gaps):
            raise ValueError("invalid reference gap code")
        safe_references.append({"family": family, "id": reference_id, "version": version,
            "status": status, "evidence_ids": sorted({_uuid(value) for value in evidence}),
            "gaps": sorted(set(gaps))})
    result["references"] = sorted(safe_references, key=lambda reference: reference["family"])
    return result
