"""Read-only G5 evidence API; audit activation is blocked until policy registry approval."""
from fastapi import APIRouter,Depends,Header,HTTPException
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.models_audit import AuditSnapshot
from mcias.api.dependencies import require_permission as guard, get_db as session_db
from mcias.services import net_audit_service as net

def perform(db,action):
    from mcias.audit_engine import PolicyBlocked
    try:return action()
    except LookupError:db.rollback();raise HTTPException(404,'Batch not found') from None
    except (PolicyBlocked,ValueError) as exc:db.rollback();raise HTTPException(409,str(exc)) from None
    except (RuntimeError,OSError):db.rollback();raise HTTPException(503,'Encrypted evidence storage unavailable') from None

router=APIRouter(prefix="/api/v1/audits",tags=["audits"])

@router.get('/batches/{batch_id}/policy-requirements')
def requirements(batch_id:str,actor=Depends(guard('claims.read','claims.review')),db=Depends(session_db)):
    return perform(db,lambda:net.requirements(db,actor,batch_id))

@router.post('/batches/{batch_id}/run',status_code=201)
def run_batch(batch_id:str,actor=Depends(guard('claims.read','claims.review')),db=Depends(session_db)):
    return perform(db,lambda:net.execute(db,actor,batch_id))

@router.get('/batches/{batch_id}/run')
def latest_batch_run(batch_id:str,actor=Depends(guard('claims.read','claims.review')),db=Depends(session_db)):
    result=perform(db,lambda:net.latest_run(db,actor,batch_id))
    if result is None:raise HTTPException(404,'No audit run recorded')
    return result

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
            "calculation":snapshot.calculation,"findings":snapshot.findings,
            "verification":snapshot.verification}
