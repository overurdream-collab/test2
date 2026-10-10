"""G6 deterministic approval workflow; no mutation of G4 or G5 records."""
from sqlalchemy import select
from mcias.models import AuditLog
from mcias.models_audit import AuditSnapshot
from mcias.models_governance_g6 import GovernanceCase,GovernanceEvent
from mcias.models_ingestion import IngestionDocument
from mcias.policy import has_permission

class GovernanceBlocked(ValueError): pass

def open_case(db,actor,snapshot_id):
    if not actor.active or not actor.organization_id or not has_permission(db,actor,"claims.read"):
        raise GovernanceBlocked("not authorized to open governance case")
    snap=db.get(AuditSnapshot,snapshot_id)
    if snap is None or snap.organization_id!=actor.organization_id:
        raise GovernanceBlocked("audit snapshot not accessible")
    case=GovernanceCase(organization_id=actor.organization_id,claim_id=snap.claim_id,
        audit_snapshot_id=snap.id,opened_by=actor.id)
    db.add(case);db.flush()
    db.add(AuditLog(actor_id=actor.id,action="g6_case_opened",resource_type="governance_case",
        resource_id=case.id,details={"snapshot_id":snap.id}))
    db.commit()
    return case

def append_event(db,actor,case_id,kind,payload,*,evidence_document_id=None):
    allowed={"propose","approve","hold","reject","object","request_reaudit"}
    if kind not in allowed or not isinstance(payload,dict):
        raise GovernanceBlocked("invalid governance action")
    permission="claims.read" if kind in {"object"} else "rules.activate"
    if not actor.active or not actor.organization_id or not has_permission(db,actor,permission):
        raise GovernanceBlocked("governance permission denied")
    case=db.scalar(select(GovernanceCase).where(GovernanceCase.id==case_id,
        GovernanceCase.organization_id==actor.organization_id).with_for_update())
    if case is None:
        raise GovernanceBlocked("case not accessible")
    latest=db.scalar(select(GovernanceEvent).where(GovernanceEvent.case_id==case.id)
        .order_by(GovernanceEvent.version.desc()).limit(1))
    if latest and latest.kind in {"approve","reject"} and kind!="object":
        raise GovernanceBlocked("final decision is immutable; file a new objection")
    if kind=="approve":
        if actor.id==case.opened_by or (latest and actor.id==latest.actor_id):
            raise GovernanceBlocked("separation of duties: self approval prohibited")
        snap=db.get(AuditSnapshot,case.audit_snapshot_id)
        if snap.calculation.get("status")!="calculated" or snap.verification.get("status")!="verified":
            raise GovernanceBlocked("held or unverified items cannot be approved")
        if latest is None or latest.kind not in {"propose","hold"}:
            raise GovernanceBlocked("proposal required before approval")
    if kind=="object":
        if not evidence_document_id:
            raise GovernanceBlocked("objection requires linked evidence")
    if evidence_document_id:
        doc=db.get(IngestionDocument,evidence_document_id)
        if doc is None or doc.organization_id!=actor.organization_id:
            raise GovernanceBlocked("evidence not accessible")
    if kind=="request_reaudit" and (latest is None or latest.kind!="object"):
        raise GovernanceBlocked("re-audit must follow an objection")
    event=GovernanceEvent(case_id=case.id,organization_id=case.organization_id,
        version=1 if latest is None else latest.version+1,kind=kind,actor_id=actor.id,
        snapshot_id=case.audit_snapshot_id,evidence_document_id=evidence_document_id,payload=payload)
    db.add(event);db.flush()
    db.add(AuditLog(actor_id=actor.id,action="g6_"+kind,resource_type="governance_event",
        resource_id=event.id,details={"case_id":case.id,"version":event.version}))
    db.commit()
    return event
