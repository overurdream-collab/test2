"""G6 append-only workflow with objected-case re-audit lineage.

Every re-audit references a separately generated G5 snapshot; never change the
original claim, audit snapshot or governance decision.
"""
from sqlalchemy import select
from mcias.models import AuditLog
from mcias.models_audit import AuditSnapshot
from mcias.models_governance_g6 import GovernanceCase, GovernanceEvent
from mcias.models_ingestion import IngestionDocument
from mcias.policy import has_permission

class GovernanceBlocked(ValueError):
    pass

PERMISSIONS = {
    "propose": "governance.propose",
    "approve": "governance.approve",
    "hold": "governance.review",
    "reject": "governance.approve",
    "object": "claims.read",
    "request_reaudit": "governance.reaudit",
    "link_reaudit": "governance.reaudit",
}

def open_case(db, actor, snapshot_id):
    if (not actor.active or not actor.organization_id
        or not has_permission(db, actor, "claims.read")):
        raise GovernanceBlocked("not authorized to open governance case")
    snap = db.get(AuditSnapshot, snapshot_id)
    if snap is None or snap.organization_id != actor.organization_id:
        raise GovernanceBlocked("audit snapshot not accessible")
    # Avoid multiple independent decisions for an identical G5 snapshot.
    existing = db.scalar(select(GovernanceCase).where(
        GovernanceCase.organization_id == actor.organization_id,
        GovernanceCase.audit_snapshot_id == snap.id).with_for_update())
    if existing:
        return existing
    case = GovernanceCase(organization_id=actor.organization_id, claim_id=snap.claim_id,
        audit_snapshot_id=snap.id, opened_by=actor.id)
    db.add(case)
    db.flush()
    db.add(AuditLog(actor_id=actor.id, action="g6_case_opened",
        resource_type="governance_case", resource_id=case.id,
        details={"snapshot_id": snap.id}))
    db.commit()
    return case

def append_event(db, actor, case_id, kind, payload, *, evidence_document_id=None):
    if kind not in PERMISSIONS or not isinstance(payload, dict):
        raise GovernanceBlocked("invalid governance action")
    allowed_keys = {"reason_code", "new_snapshot_id"} if kind == "link_reaudit" else {"reason_code"}
    if set(payload).difference(allowed_keys):
        raise GovernanceBlocked("governance event payload contains unsupported fields; use evidence attachments")
    reason_code = payload.get("reason_code")
    if reason_code is not None and (not isinstance(reason_code, str)
        or not 1 <= len(reason_code) <= 64
        or not reason_code.replace("_", "").isalnum()
        or not reason_code.isascii()):
        raise GovernanceBlocked("invalid reason code")
    permission = PERMISSIONS[kind]
    if (not actor.active or not actor.organization_id
        or not has_permission(db, actor, permission)):
        raise GovernanceBlocked("governance permission denied")
    case = db.scalar(select(GovernanceCase).where(
        GovernanceCase.id == case_id, GovernanceCase.organization_id == actor.organization_id
    ).with_for_update())
    if case is None:
        raise GovernanceBlocked("case not accessible")
    latest = db.scalar(select(GovernanceEvent).where(
        GovernanceEvent.case_id == case.id
    ).order_by(GovernanceEvent.version.desc()).limit(1))
    if latest and latest.kind in {"approve", "reject"} and kind != "object":
        raise GovernanceBlocked("final decision is immutable; file a new objection")
    if kind == "approve":
        if actor.id == case.opened_by or (latest and actor.id == latest.actor_id):
            raise GovernanceBlocked("separation of duties: self approval prohibited")
        snap = db.get(AuditSnapshot, case.audit_snapshot_id)
        if (snap is None or snap.organization_id != case.organization_id
            or snap.claim_id != case.claim_id
            or snap.calculation.get("status") != "calculated"
            or snap.verification.get("status") != "verified"):
            raise GovernanceBlocked("held or unverified items cannot be approved")
        if latest is None or latest.kind not in {"propose", "hold"}:
            raise GovernanceBlocked("proposal required before approval")
    if kind == "object" and not evidence_document_id:
        raise GovernanceBlocked("objection requires linked evidence")
    if evidence_document_id:
        doc = db.get(IngestionDocument, evidence_document_id)
        if (doc is None or doc.organization_id != actor.organization_id
            or doc.status != "extracted"
            or not isinstance(doc.sha256, str) or len(doc.sha256) != 64
            or any(c not in "0123456789abcdefABCDEF" for c in doc.sha256)):
            raise GovernanceBlocked("objection evidence not verified or quarantined")
    if kind == "request_reaudit" and (latest is None or latest.kind != "object"):
        raise GovernanceBlocked("re-audit must follow an objection")

    linked_case = None
    event_snapshot_id = case.audit_snapshot_id
    event_payload = dict(payload)
    if kind == "link_reaudit":
        if latest is None or latest.kind != "request_reaudit":
            raise GovernanceBlocked("re-audit snapshot must follow a recorded request")
        new_snapshot_id = payload.get("new_snapshot_id")
        if (not isinstance(new_snapshot_id, str) or not new_snapshot_id
            or new_snapshot_id == case.audit_snapshot_id):
            raise GovernanceBlocked("a new immutable audit snapshot is required")
        fresh = db.get(AuditSnapshot, new_snapshot_id)
        if (fresh is None or fresh.organization_id != case.organization_id
            or fresh.claim_id != case.claim_id):
            raise GovernanceBlocked("re-audit snapshot tenant or claim mismatch")
        previous = db.get(AuditSnapshot, case.audit_snapshot_id)
        if (previous is None or previous.organization_id != case.organization_id
            or not getattr(fresh, "created_at", None)
            or not getattr(previous, "created_at", None)
            or fresh.created_at <= previous.created_at):
            raise GovernanceBlocked("re-audit must be a later G5 snapshot")
        # A G5 audit must already exist; this function does not fabricate one.
        if db.scalar(select(GovernanceCase.id).where(
            GovernanceCase.organization_id == case.organization_id,
            GovernanceCase.audit_snapshot_id == fresh.id)):
            raise GovernanceBlocked("re-audit snapshot already governed")
        linked_case = GovernanceCase(organization_id=case.organization_id,
            claim_id=case.claim_id, audit_snapshot_id=fresh.id, opened_by=actor.id)
        db.add(linked_case)
        db.flush()
        event_payload = {"new_snapshot_id": fresh.id,
                         "linked_case_id": linked_case.id}
        event_snapshot_id = fresh.id

    event = GovernanceEvent(case_id=case.id, organization_id=case.organization_id,
        version=1 if latest is None else latest.version + 1, kind=kind,
        actor_id=actor.id, snapshot_id=event_snapshot_id,
        evidence_document_id=evidence_document_id, payload=event_payload)
    db.add(event)
    db.flush()
    db.add(AuditLog(actor_id=actor.id, action="g6_" + kind,
        resource_type="governance_event", resource_id=event.id,
        details={"case_id": case.id, "version": event.version,
                 "new_case_id": linked_case.id if linked_case else None}))
    db.commit()
    return event
