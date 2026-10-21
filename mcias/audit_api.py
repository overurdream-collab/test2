"""Read-only G5 evidence API; audit activation is blocked until policy registry approval."""
from fastapi import APIRouter,Depends,Header,HTTPException
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.models_audit import AuditSnapshot
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
    return {"id":snapshot.id,"claim_id":snapshot.claim_id,"policy_id":snapshot.policy_id,
            "policy_fingerprint":snapshot.policy_fingerprint,
            "calculation":snapshot.calculation,"findings":(
                project_audit_findings(snapshot.findings)
                if "audit_state" in snapshot.findings else snapshot.findings),
            "verification":snapshot.verification}
