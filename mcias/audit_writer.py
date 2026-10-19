"""Shared bounded audit writer for MCIAS components.

Success events join the caller's business transaction. Rejected/error attempts
must be recorded AFTER caller rollback using record_outcome_independent().
Never log secrets, patient fields, unbounded objects, or external free text.
"""
from sqlalchemy.orm import Session
from mcias.models import AuditLog, User

_ALLOWED = {"version", "previous_version", "previous_id", "new_id",
            "effective_from", "effective_until", "reason_code",
            "contract_number", "status"}
_MAX = 150

def _safe_details(details):
    if not isinstance(details, dict):
        return {}
    clean = {}
    for key, value in details.items():
        if key not in _ALLOWED:
            continue
        if not isinstance(value, (str, int, bool)) or len(str(value)) > _MAX:
            continue
        clean[key] = value
    return clean

def write_event(db: Session, *, actor: User, organization_id: str,
                action: str, resource_type: str, resource_id: str | None,
                outcome: str, details: dict | None = None):
    """Stage one immutable event in the *current* business transaction."""
    if not actor.active or not actor.organization_id or actor.organization_id != organization_id:
        raise ValueError("audit actor/organization mismatch")
    if outcome not in {"success", "denied", "error"}:
        raise ValueError("invalid audit outcome")
    if not action or len(action) > 120 or not resource_type or len(resource_type) > 90:
        raise ValueError("invalid audit event")
    record = AuditLog(actor_id=actor.id, action=action, resource_type=resource_type,
                      resource_id=resource_id,
                      details={"organization_id": organization_id, "outcome": outcome,
                               **_safe_details(details or {})})
    db.add(record)
    db.flush()
    return record

def record_outcome_independent(bind, *, actor_id: str, organization_id: str,
                               action: str, resource_type: str,
                               resource_id: str | None, outcome: str,
                               details: dict | None = None):
    """Durable denial/error event in separate transaction after business rollback.

    The caller passes only established server-side actor and tenant identifiers.
    Failure to persist raises: never pretend that rejected actions were audited.
    """
    with Session(bind) as independent:
        actor = independent.get(User, actor_id)
        if actor is None:
            raise ValueError("audit actor unavailable")
        result = write_event(independent, actor=actor, organization_id=organization_id,
                             action=action, resource_type=resource_type,
                             resource_id=resource_id, outcome=outcome, details=details)
        event_id = result.id
        independent.commit()
        return event_id
