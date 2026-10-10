"""G8 independent reviewer feedback; records quality of review signals, not fraud."""
import re
from hashlib import sha256
from sqlalchemy import select

from mcias.models import AuditLog
from mcias.models_g8 import AnalysisRun, AnalysisSignalReview
from mcias.intelligence_g8 import IntelligenceBlocked, digest
from mcias.intelligence_service_g8 import _authorize, verify_run

DISPOSITIONS=frozenset({"false_positive","needs_followup","insufficient_evidence"})
REASONS=frozenset({
    "DATA_QUALITY", "CONTEXT_EXPLAINS", "NOT_REPRODUCIBLE",
    "NEEDS_SOURCE_REVIEW", "NEEDS_POLICY_REVIEW", "OTHER_REVIEW",
})

def _run(db, actor, run_id, lock=False):
    query=select(AnalysisRun).where(
        AnalysisRun.id==run_id,
        AnalysisRun.organization_id==actor.organization_id)
    if lock:
        query=query.with_for_update()
    run=db.scalar(query)
    if run is None:
        raise IntelligenceBlocked("G8 analysis run not accessible")
    verify_run(run)
    if run.kind!="signals":
        raise IntelligenceBlocked("only G8 review signals may receive an assessment")
    findings=run.result.get("output",{}).get("findings",[])
    if not isinstance(findings,list):
        raise IntelligenceBlocked("invalid G8 signal results")
    return run,findings

def add_review(db,actor,run_id,signal_index,disposition,reason_code):
    _authorize(db,actor,"intelligence.review")
    if (type(signal_index) is not int or signal_index<0
        or disposition not in DISPOSITIONS
        or reason_code not in REASONS):
        raise IntelligenceBlocked("invalid signal assessment; coded reasons only")
    run,findings=_run(db,actor,run_id,lock=True)
    if actor.id==run.created_by:
        raise IntelligenceBlocked("independent reviewer required")
    if signal_index>=len(findings):
        raise IntelligenceBlocked("signal index out of range")
    finding=findings[signal_index]
    if finding.get("status")!="review_only":
        raise IntelligenceBlocked("cannot assess a non-review signal")
    last=db.scalar(select(AnalysisSignalReview).where(
        AnalysisSignalReview.run_id==run.id,
        AnalysisSignalReview.organization_id==actor.organization_id,
        AnalysisSignalReview.signal_index==signal_index
    ).order_by(AnalysisSignalReview.version.desc()).limit(1))
    review=AnalysisSignalReview(organization_id=actor.organization_id,
        run_id=run.id,signal_index=signal_index,
        version=(last.version+1 if last else 1),
        disposition=disposition,reviewer_id=actor.id,
        evidence={"reason_code":reason_code,
                  "signal_fingerprint":digest(finding),
                  "analysis_fingerprint":run.fingerprint,
                  "review_only":True})
    db.add(review)
    db.flush()
    db.add(AuditLog(actor_id=actor.id,action="g8_signal_review_recorded",
        resource_type="g8_signal_review",resource_id=review.id,
        details={"run_id":run.id,"signal_index":signal_index,
                 "version":review.version,"disposition":disposition}))
    db.commit()
    return review

def reviews_summary(db,actor,run_id):
    _authorize(db,actor,"intelligence.read")
    run,findings=_run(db,actor,run_id)
    history=db.scalars(select(AnalysisSignalReview).where(
        AnalysisSignalReview.organization_id==actor.organization_id,
        AnalysisSignalReview.run_id==run.id
    ).order_by(AnalysisSignalReview.signal_index,AnalysisSignalReview.version)).all()
    latest={}
    for item in history:
        if (item.signal_index>=len(findings)
            or item.evidence.get("signal_fingerprint")!=digest(findings[item.signal_index])
            or item.evidence.get("analysis_fingerprint")!=run.fingerprint):
            raise IntelligenceBlocked("G8 review evidence integrity mismatch")
        latest[item.signal_index]=item
    counts={key:0 for key in DISPOSITIONS}
    for entry in latest.values():
        counts[entry.disposition]+=1
    reviewed=len(latest)
    return {"run_id":run.id,"review_only":True,
            "signal_count":len(findings),"reviewed_signals":reviewed,
            "unreviewed_signals":len(findings)-reviewed,
            "by_disposition":counts,
            "false_positive_rate_among_reviewed":(
                str(__import__("decimal").Decimal(counts["false_positive"])*
                    100/__import__("decimal").Decimal(reviewed))
                if reviewed else None),
            "denominator":"reviewed_signals_only",
            "interpretation":"quality_feedback_not_fraud_verdict",
            "items":[{"signal_index":key,"version":entry.version,
                      "disposition":entry.disposition,
                      "reason_code":entry.evidence["reason_code"]}
                     for key,entry in sorted(latest.items())]}
