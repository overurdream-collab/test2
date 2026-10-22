"""G5 evidence API and server-controlled advisory review; no financial execution."""
from fastapi import APIRouter,Body,Depends,Header,HTTPException
from pydantic import BaseModel,ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.models import MFAFactor,Role,UserRole
from mcias.models_claims import ClaimEntry
from mcias.models_audit import AuditSnapshot
from mcias.audit_engine import PolicyBlocked
from mcias.audit_service import run_audit
from mcias.audit_agents import project_audit_findings

router=APIRouter(prefix="/api/v1/audits",tags=["audits"])

@router.get("/{snapshot_id}")
def get_snapshot(snapshot_id:str,authorization:str|None=Header(default=None),
                 db:Session=Depends(get_db)):
    actor,_=resolve_user(db,authorization)
    snapshot=db.get(AuditSnapshot,snapshot_id)
    if snapshot is None or snapshot.organization_id!=actor.organization_id:
        raise HTTPException(404,"audit snapshot not found")
    require_organization(db,actor,snapshot.organization_id,"claims.read")
    return _snapshot_payload(snapshot)


def _snapshot_payload(snapshot):
    return {"id":snapshot.id,"claim_id":snapshot.claim_id,"policy_id":snapshot.policy_id,
            "policy_fingerprint":snapshot.policy_fingerprint,
            "calculation":snapshot.calculation,"findings":(
                project_audit_findings(snapshot.findings)
                if "audit_state" in snapshot.findings else snapshot.findings),
            "verification":snapshot.verification}


class AdvisoryReviewRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")


@router.post("/claims/{claim_id}/review")
def review_claim(claim_id:str,payload:AdvisoryReviewRequest|None=Body(default=None),
                 authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    actor,_=resolve_user(db,authorization)
    require_organization(db,actor,actor.organization_id,"claims.read")
    role=db.scalar(select(Role.id).join(UserRole,UserRole.role_id==Role.id).where(
        UserRole.user_id==actor.id,Role.code=="super_admin"))
    factor=db.get(MFAFactor,actor.id)
    if not role or factor is None or not factor.enabled or factor.last_accepted_counter<0:
        raise HTTPException(403,"active Super Admin with verified MFA required")
    claim=db.scalar(select(ClaimEntry).where(ClaimEntry.id==claim_id,
        ClaimEntry.organization_id==actor.organization_id))
    if claim is None:
        raise HTTPException(404,"claim not found")
    try:
        snapshot=run_audit(db,actor,claim.id,review_only=True)
    except PolicyBlocked as exc:
        db.rollback()
        raise HTTPException(403,str(exc)) from exc
    return _snapshot_payload(snapshot)
