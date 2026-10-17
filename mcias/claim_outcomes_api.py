"""Four mutually exclusive, read-only CSV audit triage exports."""
from io import BytesIO
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.models_claims import ClaimBatch, ClaimEntry
from mcias.models_audit import AuditSnapshot
from mcias.claim_outcomes import KINDS, classify_claims, export_csv, summarize

router = APIRouter(prefix="/api/v1/audit-outcomes", tags=["four-way audit triage"])


def _rows(db, authorization, batch_id, permission):
    actor, _ = resolve_user(db, authorization)
    if not actor.organization_id:
        raise HTTPException(403, "organization required")
    require_organization(db, actor, actor.organization_id, permission)
    require_organization(db, actor, actor.organization_id, "claims.read")
    batch = db.scalar(select(ClaimBatch).where(ClaimBatch.id == batch_id,
                                              ClaimBatch.organization_id == actor.organization_id))
    if batch is None:
        raise HTTPException(404, "batch not found")
    claims = db.scalars(select(ClaimEntry).where(
        ClaimEntry.organization_id == actor.organization_id, ClaimEntry.batch_id == batch_id
    ).order_by(ClaimEntry.id)).all()
    ids = [c.id for c in claims]
    snapshots = db.scalars(select(AuditSnapshot).where(
        AuditSnapshot.organization_id == actor.organization_id,
        AuditSnapshot.claim_id.in_(ids))).all() if ids else []
    return classify_claims(claims, snapshots)


@router.get("/batches/{batch_id}/summary")
def batch_outcomes(batch_id: str, authorization: str | None = Header(default=None),
                   db: Session = Depends(get_db)):
    return summarize(_rows(db, authorization, batch_id, "reports.read"))


@router.get("/batches/{batch_id}/export/{outcome}")
def export_batch_outcome(batch_id: str, outcome: str,
                         authorization: str | None = Header(default=None),
                         db: Session = Depends(get_db)):
    if outcome not in KINDS:
        raise HTTPException(404, "unsupported outcome")
    rows = _rows(db, authorization, batch_id, "reports.export")
    payload = export_csv(rows, outcome)
    return StreamingResponse(BytesIO(payload), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="mcias-' + outcome.lower() + '.csv"',
                 "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
