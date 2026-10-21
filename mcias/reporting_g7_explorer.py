"""G7 read-only report explorer. No raw medical/source fields in drilldowns."""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Literal
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.models_reporting_g7 import ReportSnapshot
from mcias.reporting_g7 import verify_snapshot, ReportBlocked

router = APIRouter(prefix="/api/v1/report-explorer", tags=["report-explorer"])

def authorized(db, authorization, permission="reports.read"):
    user, _ = resolve_user(db, authorization)
    if not user.organization_id:
        raise HTTPException(403, "organization required")
    require_organization(db, user, user.organization_id, permission)
    return user

def metadata(snapshot):
    return {"id": snapshot.id, "batch_id": snapshot.batch_id,
            "version": snapshot.version, "fingerprint": snapshot.fingerprint,
            "summary": snapshot.summary,
            "source_sha256": snapshot.dataset["source_sha256"]}

@router.get("/snapshots")
def list_snapshots(batch_id: str | None = Query(default=None, min_length=1, max_length=36),
                   limit: int = Query(20, ge=1, le=100),
                   offset: int = Query(0, ge=0),
                   authorization: str | None = Header(default=None),
                   db: Session = Depends(get_db)):
    user = authorized(db, authorization)
    query = select(ReportSnapshot).where(
        ReportSnapshot.organization_id == user.organization_id)
    if batch_id:
        query = query.where(ReportSnapshot.batch_id == batch_id)
    records = db.scalars(query.order_by(ReportSnapshot.created_at.desc(),
             ReportSnapshot.id.desc()).offset(offset).limit(limit + 1)).all()
    for report in records:
        try:
            verify_snapshot(report)
        except ReportBlocked as exc:
            raise HTTPException(409, str(exc)) from exc
    return {"items": [metadata(record) for record in records[:limit]],
            "has_more": len(records) > limit, "offset": offset, "limit": limit}

@router.get("/snapshots/{report_id}/entries")
def entries(report_id: str,
            state: Literal["approved", "held"] | None = Query(default=None),
            currency: str | None = Query(default=None, pattern=r"^[A-Z]{3}$"),
            limit: int = Query(50, ge=1, le=100),
            offset: int = Query(0, ge=0),
            authorization: str | None = Header(default=None),
            db: Session = Depends(get_db),
            audit_state: Literal["MATCH_VERIFIED", "VIOLATION_PROVEN", "UNRESOLVED", "AUDIT_UNAVAILABLE"] | None = None):
    user = authorized(db, authorization, "reports.details.read")
    require_organization(db, user, user.organization_id, "reports.read")
    report = db.get(ReportSnapshot, report_id)
    if report is None or report.organization_id != user.organization_id:
        raise HTTPException(404, "report not found")
    try:
        verify_snapshot(report)
    except ReportBlocked as exc:
        raise HTTPException(409, str(exc)) from exc
    filtered = [row for row in report.dataset["rows"]
                if (state is None or row["state"] == state)
                and (audit_state is None or row.get("audit_state") == audit_state)
                and (currency is None or row["currency"] == currency)]
    fields = ("claim_id", "currency", "claimed", "state",
              "hold_reason", "payable", "deduction",
              "audit_snapshot_id", "governance_case_id", "governance_event_id", "governance_event_version",
              "audit_state", "audit_state_schema_version", "source_audit_state_schema_version",
              "audit_reason_code", "completed_audit", "audit_coverage", "audit_references", "audit_rules",
              "complete_reference_count", "source_evidence_verified", "audit_event_ids",
              "source_document_id", "source_record_id", "source_sha256", "source_position")
    return {"report_id": report.id, "version": report.version,
            "total": len(filtered), "offset": offset, "limit": limit,
            "items": [{key: row.get(key) for key in fields}
                      for row in filtered[offset:offset + limit]]}
