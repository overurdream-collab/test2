"""G7 authenticated reporting APIs; original field export fails closed."""
from io import BytesIO
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization, require_sensitive_field
from mcias.models_reporting_g7 import ReportSnapshot
from mcias.reporting_g7 import create_snapshot, verify_snapshot, beneficiary_statement, ReportBlocked
from mcias.report_exports_g7 import render_xlsx, render_pdf

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

def _actor(db, authorization, permission):
    actor, _ = resolve_user(db, authorization)
    if not actor.organization_id:
        raise HTTPException(403, "organization required")
    require_organization(db, actor, actor.organization_id, permission)
    return actor

def _report(db, actor, report_id):
    report = db.get(ReportSnapshot, report_id)
    if report is None or report.organization_id != actor.organization_id:
        raise HTTPException(404, "report not found")
    try:
        verify_snapshot(report)
    except ReportBlocked as exc:
        raise HTTPException(409, str(exc)) from exc
    return report

def _metadata(report):
    return {"id": report.id, "batch_id": report.batch_id,
            "version": report.version, "fingerprint": report.fingerprint,
            "summary": report.summary,
            "source_sha256": report.dataset["source_sha256"]}

@router.post("/batches/{batch_id}/snapshots", status_code=201)
def freeze_report(batch_id: str, authorization: str | None = Header(default=None),
                  db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "reports.create")
    require_organization(db, actor, actor.organization_id, "claims.read")
    try:
        return _metadata(create_snapshot(db, actor, batch_id))
    except ReportBlocked as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc

@router.get("/snapshots/{report_id}")
def report_details(report_id: str, authorization: str | None = Header(default=None),
                   db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "reports.read")
    return _metadata(_report(db, actor, report_id))

@router.get("/snapshots/{report_id}/dashboard")
def dashboard(report_id: str, authorization: str | None = Header(default=None),
              db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "reports.read")
    return _metadata(_report(db, actor, report_id))

@router.get("/snapshots/{report_id}/excel")
def download_excel(report_id: str, include_originals: bool = Query(False),
                   authorization: str | None = Header(default=None),
                   db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "reports.export")
    report = _report(db, actor, report_id)
    if include_originals:
        require_organization(db, actor, actor.organization_id, "reports.originals.export")
        fields = {key for row in report.dataset["rows"] for key in row["source_values"]}
        for field in sorted(fields):
            # No guessed field permissions: unregistered names fail closed.
            require_sensitive_field(db, actor, actor.organization_id, field)
    try:
        data = render_xlsx(report, include_originals=include_originals)
    except ReportBlocked as exc:
        raise HTTPException(409, str(exc)) from exc
    return StreamingResponse(BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="mcias-report.xlsx"',
                 "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

@router.get("/snapshots/{report_id}/pdf")
def download_pdf(report_id: str, authorization: str | None = Header(default=None),
                 db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "reports.export")
    report = _report(db, actor, report_id)
    try:
        data = render_pdf(report)
    except ReportBlocked as exc:
        raise HTTPException(409, str(exc)) from exc
    return StreamingResponse(BytesIO(data), media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="mcias-report.pdf"',
                 "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

@router.get("/snapshots/{report_id}/beneficiaries/{token}/statement")
def statement(report_id: str, token: str, authorization: str | None = Header(default=None),
              db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "reports.beneficiary.read")
    require_sensitive_field(db, actor, actor.organization_id, "beneficiary_token")
    try:
        return beneficiary_statement(_report(db, actor, report_id), token)
    except ReportBlocked as exc:
        raise HTTPException(409, str(exc)) from exc
