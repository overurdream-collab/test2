"""Bounded audit metadata validation. Phase 2A: no schema change."""
import re
from uuid import uuid4

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
