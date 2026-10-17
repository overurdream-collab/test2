"""Exclusive, read-only four-way rule triage; not payment/medical approval."""
import csv
import io
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.models_claims import ClaimEntry, ClaimBatch
from mcias.models_audit import AuditSnapshot

router = APIRouter(prefix="/api/v1/audit-triage", tags=["Review-only triage"])
GROUPS = ("REJECTED_RULE_CERTAIN", "ACCEPTED_RULES", "MISSING_ATTACHMENTS", "HUMAN_REVIEW")

def classify_snapshot(snapshot):
    if snapshot is None:
        return "HUMAN_REVIEW", "no_audit_snapshot"
    checks = snapshot.findings.get("agents", []) if isinstance(snapshot.findings, dict) else []
    if not isinstance(checks, list) or len(checks) != 8:
        return "HUMAN_REVIEW", "incomplete_rule_evidence"
    # Deliberately require an explicit, independently verified violation flag.
    # Current G5 'hold' is NOT proof of a definite contractual rejection.
    for finding in checks:
        if (isinstance(finding, dict) and finding.get("status") == "fail_confirmed"
            and finding.get("independently_verified") is True
            and finding.get("approved_rule_version_id") and finding.get("evidence_ref")):
            return "REJECTED_RULE_CERTAIN", str(finding.get("agent", "confirmed_rule"))
    if any(isinstance(x, dict) and x.get("agent") == "evidence" and x.get("status") == "hold"
           for x in checks):
        return "MISSING_ATTACHMENTS", "required_attachment_not_linked"
    if (all(isinstance(x, dict) and x.get("status") == "pass" for x in checks)
        and isinstance(snapshot.verification, dict) and snapshot.verification.get("status") == "verified"
        and isinstance(snapshot.calculation, dict) and snapshot.calculation.get("status") == "calculated"):
        return "ACCEPTED_RULES", "rule_checks_passed_review_only"
    return "HUMAN_REVIEW", "unresolved_rule_or_reference"

def _rows(db, actor, batch_id):
    batch = db.get(ClaimBatch, batch_id)
    if batch is None or batch.organization_id != actor.organization_id:
        raise HTTPException(404, "batch not found")
    claims = db.scalars(select(ClaimEntry).where(ClaimEntry.batch_id == batch.id,
                      ClaimEntry.organization_id == actor.organization_id).order_by(ClaimEntry.id)).all()
    claim_ids = [c.id for c in claims]
    snapshots = db.scalars(select(AuditSnapshot).where(AuditSnapshot.organization_id == actor.organization_id,
                                  AuditSnapshot.claim_id.in_(claim_ids))
                        .order_by(AuditSnapshot.created_at.desc(), AuditSnapshot.id.desc())).all() if claims else []
    newest = {}
    for snapshot in snapshots:
        newest.setdefault(snapshot.claim_id, snapshot)
    result = []
    for claim in claims:
        snap = newest.get(claim.id)
        group, reason = classify_snapshot(snap)
        result.append({
            "claim_id": claim.id, "audit_snapshot_id": snap.id if snap else "",
            "provider_code": claim.provider_code, "service_date": claim.service_date.isoformat(),
            "claimed_amount": str(claim.claimed_amount), "currency": claim.currency,
            "classification": group, "reason_code": reason,
            "review_only": True,
        })
    return result

def _actor(db, authorization):
    actor, _ = resolve_user(db, authorization)
    require_organization(db, actor, actor.organization_id, "claims.read")
    require_organization(db, actor, actor.organization_id, "reports.read")
    return actor

@router.get("/batches/{batch_id}/summary")
def summary(batch_id: str, authorization: str | None = Header(default=None),
            db: Session = Depends(get_db)):
    actor = _actor(db, authorization)
    rows = _rows(db, actor, batch_id)
    return {"batch_id": batch_id, "total_claims": len(rows),
            "counts": {group: sum(row["classification"] == group for row in rows) for group in GROUPS},
            "file_types": list(GROUPS),
            "review_only": True,
            "notice": "No automatic payment or contractual rejection; snapshots retain their own governance."}

@router.get("/batches/{batch_id}/files/{group}.csv")
def export_csv(batch_id: str, group: str, authorization: str | None = Header(default=None),
               db: Session = Depends(get_db)):
    actor = _actor(db, authorization)
    if group not in GROUPS:
        raise HTTPException(404, "unknown classification")
    rows = [row for row in _rows(db, actor, batch_id) if row["classification"] == group]
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.DictWriter(buffer, fieldnames=[
        "claim_id", "audit_snapshot_id", "provider_code", "service_date",
        "claimed_amount", "currency", "classification", "reason_code", "review_only"])
    writer.writeheader()
    for row in rows:
        # Protect CSV consumers from interpreting any externally sourced value as a formula.
        writer.writerow({k: ("'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v)
                         for k, v in row.items()})
    return Response(buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="mcias_{group.lower()}.csv"',
                             "Cache-Control": "no-store"})
