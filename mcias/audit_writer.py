"""Shared bounded audit writer for MCIAS components.

Success events join the caller's business transaction. Rejected/error attempts
must be recorded AFTER caller rollback using record_outcome_independent().
Never log secrets, patient fields, unbounded objects, or external free text.
"""
from uuid import NAMESPACE_URL, uuid5
from sqlalchemy.orm import Session
from mcias.models import AuditLog, User
from mcias.audit_contract import (validate_event, clean_details, clean_claim_audit_details,
                                  CLAIM_AUDIT_ACTION, _uuid)

_ALLOWED = {"version", "previous_version", "previous_id", "new_id",
            "effective_from", "effective_until", "reason_code",
            "contract_number", "status"}
_MAX = 150

def _safe_details(details):
    return clean_details(details)

def write_event(db: Session, *, actor: User, organization_id: str,
                action: str, resource_type: str, resource_id: str | None,
                outcome: str, details: dict | None = None):
    """Stage one immutable event in the *current* business transaction."""
    if not actor.active or not actor.organization_id or actor.organization_id != organization_id:
        raise ValueError("audit actor/organization mismatch")
    validate_event(action, resource_type, resource_id, outcome)
    if action == CLAIM_AUDIT_ACTION:
        if resource_type != "claim_entry" or outcome != "success":
            raise ValueError("invalid claim audit event")
        _uuid(resource_id)
        safe_details = clean_claim_audit_details(details)
        _validate_claim_correlation(db, organization_id, resource_id, safe_details)
        return _write_claim_event(db, actor, organization_id, resource_id, safe_details)
    record = AuditLog(actor_id=actor.id, action=action, resource_type=resource_type,
                      resource_id=resource_id,
                      details={"organization_id": organization_id, "outcome": outcome,
                               **_safe_details(details or {})})
    db.add(record)
    db.flush()
    return record


def _validate_claim_correlation(db, organization_id, claim_id, details):
    from mcias.models_audit import AuditSnapshot
    from mcias.models_claims import ClaimBatch, ClaimEntry
    from mcias.models_ingestion import IngestionDocument
    snapshot = db.get(AuditSnapshot, details["audit_snapshot_id"])
    claim = db.get(ClaimEntry, claim_id)
    if (snapshot is None or claim is None or snapshot.organization_id != organization_id
        or claim.organization_id != organization_id or snapshot.claim_id != claim_id
        or snapshot.policy_fingerprint != details["policy_fingerprint"]
        or snapshot.findings.get("audit_state") != details["audit_state"]
        or claim.extracted_record_id != details["source_record_id"]):
        raise ValueError("claim audit snapshot correlation mismatch")
    certificates = snapshot.findings.get("reference_certificates")
    if not isinstance(certificates, list):
        raise ValueError("claim audit reference correlation missing")
    try:
        projected = [{"family": certificate["family"], "id": certificate["reference_id"],
            "version": certificate["version"], "status": certificate["lookup_status"],
            "evidence_ids": sorted({evidence[key] for evidence in certificate["source_evidence"]
                for key in ("source_id", "authorization_id") if evidence.get(key)}),
            "gaps": certificate["gaps"]} for certificate in certificates]
        expected = clean_claim_audit_details({**details, "references": projected})["references"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid snapshot reference correlation") from exc
    if expected != details["references"]:
        raise ValueError("claim audit reference correlation mismatch")
    if ("policy_version" in details
        and details["policy_version"] != snapshot.findings.get("policy_version")):
        raise ValueError("claim audit policy version correlation mismatch")
    batch = db.get(ClaimBatch, claim.batch_id)
    document = db.get(IngestionDocument, details["document_id"])
    if (batch is None or document is None or batch.organization_id != organization_id
        or document.organization_id != organization_id
        or batch.ingestion_document_id != document.id
        or batch.source_sha256 != details["source_sha256"]
        or document.sha256 != details["source_sha256"]):
        raise ValueError("claim audit source correlation mismatch")


def _write_claim_event(db, actor, organization_id, claim_id, details):
    """Deduplicate this snapshot event atomically on the existing AuditLog PK.

    The UUID names an immutable snapshot, not an HTTP attempt. It provides no
    general request-id/UNKNOWN recovery guarantee and performs no inner commit.
    """
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif db.bind.dialect.name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise ValueError("claim audit persistence dialect unsupported")
    event_id = str(uuid5(NAMESPACE_URL,
        f"mcias:{CLAIM_AUDIT_ACTION}:{organization_id}:{details['audit_snapshot_id']}"))
    payload = {"organization_id": organization_id, "outcome": "success", **details}
    db.execute(insert(AuditLog).values(id=event_id, actor_id=actor.id,
        action=CLAIM_AUDIT_ACTION, resource_type="claim_entry", resource_id=claim_id,
        details=payload).on_conflict_do_nothing(index_elements=["id"]))
    record = db.get(AuditLog, event_id)
    if (record is None or record.action != CLAIM_AUDIT_ACTION or record.resource_type != "claim_entry"
        or record.resource_id != claim_id or record.details != payload):
        raise ValueError("conflicting claim audit event for immutable snapshot")
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
