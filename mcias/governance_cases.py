"""G6 controlled governance decisions and objection provenance."""
from sqlalchemy import select,func
from mcias.models import AuditLog
from mcias.models_audit import AuditSnapshot
from mcias.models_claims import ClaimEntry
from mcias.models_governance import GovernanceCase,GovernanceDecision,GovernanceObjection

class GovernanceBlocked(ValueError): pass

def open_case(db,actor,snapshot_id):
    snapshot=db.scalar(select(AuditSnapshot).where(AuditSnapshot.id==snapshot_id,
        AuditSnapshot.organization_id==actor.organization_id))
    if not actor.active or snapshot is None:
        raise GovernanceBlocked("snapshot not accessible")
    item=GovernanceCase(organization_id=actor.organization_id,
        audit_snapshot_id=snapshot.id,proposed_by=actor.id)
    db.add(item);db.flush()
    db.add(AuditLog(actor_id=actor.id,action="g6_case_opened",
        resource_type="governance_case",resource_id=item.id))
    db.commit()
    return item

def decide(db,actor,case_id,*,stage,decision,evidence):
    if decision not in ("approved","held","rejected") or not stage or not isinstance(evidence,dict):
        raise GovernanceBlocked("invalid decision")
    case=db.scalar(select(GovernanceCase).where(GovernanceCase.id==case_id,
        GovernanceCase.organization_id==actor.organization_id).with_for_update())
    if case is None or not actor.active:
        raise GovernanceBlocked("case not accessible")
    if case.proposed_by==actor.id:
        raise GovernanceBlocked("self approval prohibited")
    if case.state!="pending":
        raise GovernanceBlocked("case not pending")
    snapshot=db.get(AuditSnapshot,case.audit_snapshot_id)
    if snapshot is None or snapshot.organization_id!=case.organization_id:
        raise GovernanceBlocked("snapshot tenant mismatch")
    if decision=="approved" and (snapshot.calculation.get("status")!="calculated"
        or snapshot.verification.get("status")!="verified"):
        raise GovernanceBlocked("held or unverified claims cannot be approved")
    version=(db.scalar(select(func.max(GovernanceDecision.version)).where(
        GovernanceDecision.case_id==case.id)) or 0)+1
    record=GovernanceDecision(case_id=case.id,organization_id=case.organization_id,
        version=version,stage=stage,decision=decision,actor_id=actor.id,evidence=evidence)
    db.add(record)
    if decision!="held":
        case.state=decision
    db.flush()
    db.add(AuditLog(actor_id=actor.id,action="g6_decision_recorded",
        resource_type="governance_decision",resource_id=record.id,
        details={"case_id":case.id,"version":version,"decision":decision}))
    db.commit()
    return record

def object_to_claim(db,actor,case_id,claim_id,document_id):
    from mcias.models_ingestion import IngestionDocument
    case=db.scalar(select(GovernanceCase).where(GovernanceCase.id==case_id,
        GovernanceCase.organization_id==actor.organization_id))
    if case is None or not actor.active:
        raise GovernanceBlocked("case not accessible")
    snapshot=db.get(AuditSnapshot,case.audit_snapshot_id)
    claim=db.scalar(select(ClaimEntry).where(ClaimEntry.id==claim_id,
        ClaimEntry.organization_id==actor.organization_id))
    document=db.get(IngestionDocument,document_id)
    if (snapshot is None or claim is None or claim.id!=snapshot.claim_id
        or document is None or document.organization_id!=actor.organization_id):
        raise GovernanceBlocked("objection source or claim mismatch")
    objection=GovernanceObjection(case_id=case.id,organization_id=actor.organization_id,
        claim_id=claim.id,document_id=document.id,submitted_by=actor.id)
    db.add(objection)
    case.state="pending"
    db.flush()
    db.add(AuditLog(actor_id=actor.id,action="g6_objection_received",
        resource_type="governance_objection",resource_id=objection.id,
        details={"claim_id":claim.id,"document_id":document.id,"re_audit_required":True}))
    db.commit()
    return objection
