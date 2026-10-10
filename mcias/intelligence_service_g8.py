"""G8 Analysis Studio and immutable run orchestration.

Server-enforced task permission gates, documented synthetic test evidence,
independent activation and source-only deterministic analytics. No SQL/LLM
execution, clinical assessments, payment orders or unsanctioned data sources.
"""
import re
from types import SimpleNamespace
from sqlalchemy import select
from mcias.models import AuditLog, Organization
from mcias.models_claims import ClaimEntry
from mcias.models_reporting_g7 import ReportSnapshot
from mcias.models_g8 import AnalysisTaskVersion, AnalysisTaskEvent, AnalysisRun
from mcias.policy import has_permission
from mcias.intelligence_g8 import (
    IntelligenceBlocked, SOURCE, validate_config, canonical, digest,
    aggregate, signals, simulate, assemble, ENGINE_VERSION,
)

TASK_CODE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
BUILTIN_KINDS = frozenset({"summary", "simulation", "signals"})

def _authorize(db, actor, permission):
    if (not getattr(actor, "active", False) or not getattr(actor, "organization_id", None)
        or not has_permission(db, actor, permission)):
        raise IntelligenceBlocked("G8 permission denied")
    return actor.organization_id

def _task(db, actor, task_id, lock=False):
    query = select(AnalysisTaskVersion).where(
        AnalysisTaskVersion.id == task_id,
        AnalysisTaskVersion.organization_id == actor.organization_id)
    if lock:
        query = query.with_for_update()
    task = db.scalar(query)
    if task is None:
        raise IntelligenceBlocked("analysis task not accessible")
    if digest(task.configuration) != task.fingerprint:
        raise IntelligenceBlocked("analysis task configuration integrity failed")
    validate_config(task.configuration)
    return task

def _last_event(db, task):
    return db.scalar(select(AnalysisTaskEvent).where(
        AnalysisTaskEvent.task_id == task.id,
        AnalysisTaskEvent.organization_id == task.organization_id
    ).order_by(AnalysisTaskEvent.version.desc()).limit(1))

def task_status(db, task):
    event = _last_event(db, task)
    return event.kind if event else "draft"

def create_task(db, actor, code, configuration):
    org = _authorize(db, actor, "intelligence.studio.manage")
    if type(code) is not str or not TASK_CODE.fullmatch(code):
        raise IntelligenceBlocked("invalid task code")
    config = validate_config(configuration)
    # PostgreSQL org lock serializes competing versions of the same task code.
    organization = db.scalar(select(Organization).where(
        Organization.id == org).with_for_update())
    if organization is None:
        raise IntelligenceBlocked("organization missing")
    existing = db.scalar(select(AnalysisTaskVersion).where(
        AnalysisTaskVersion.organization_id == org,
        AnalysisTaskVersion.code == code
    ).order_by(AnalysisTaskVersion.version.desc()).limit(1))
    task = AnalysisTaskVersion(organization_id=org, code=code,
        version=(existing.version + 1 if existing else 1),
        configuration=config, fingerprint=digest(config), created_by=actor.id)
    db.add(task)
    db.flush()
    db.add(AuditLog(actor_id=actor.id, action="g8_task_draft",
        resource_type="g8_analysis_task", resource_id=task.id,
        details={"code": code, "version": task.version,
                 "configuration_fingerprint": task.fingerprint}))
    db.commit()
    return task

def _fixture():
    """Synthetic cohort: 10 provider A (8 held), 10 provider B (2 held)."""
    rows = []
    for provider in ("A", "B"):
        for number in range(10):
            held = number < (8 if provider == "A" else 2)
            rows.append({"claim_id": provider + str(number), "provider": provider,
                "service": "synthetic", "month": "2026-01", "currency": "YER",
                "state": "held" if held else "approved",
                "claimed": __import__("decimal").Decimal("100"),
                "payable": __import__("decimal").Decimal(0 if held else 80),
                "deductions": __import__("decimal").Decimal(0 if held else 20)})
    return rows

def _verified_test(config):
    """Internal reproducible G8 smoke suite; users cannot claim it passed."""
    cfg = dict(validate_config(config))
    cfg["threshold_percent"] = "40"
    cfg["min_group_size"] = 5
    sample = _fixture()
    positive = signals(sample, cfg)
    if (positive["status"] != "review_only" or not positive["no_automatic_deductions"]
        or not positive["false_positive_review_required"]):
        raise IntelligenceBlocked("G8 synthetic positive test failed")
    if cfg["dimension"] == "provider" and not positive["findings"]:
        raise IntelligenceBlocked("G8 synthetic signal test failed")
    # Negative control: threshold 100% cannot generate an alert.
    control = dict(cfg, threshold_percent="100")
    negative = signals(sample, control)
    if negative["findings"]:
        raise IntelligenceBlocked("G8 synthetic negative control failed")
    return {"engine": ENGINE_VERSION, "fixture_id": "G8_SYNTHETIC_20_V1",
            "positive_digest": digest(positive),
            "negative_digest": digest(negative),
            "positive_findings": len(positive["findings"]),
            "negative_findings": len(negative["findings"]),
            "fixture_data_sha256": digest([
                {k: str(v) if k in ("claimed", "payable", "deductions") else v
                 for k, v in row.items()} for row in sample]),
            "verification": "deterministic_controls_passed"}

def _append_event(db, actor, task, kind, evidence, latest):
    event = AnalysisTaskEvent(organization_id=task.organization_id,
        task_id=task.id, version=latest.version + 1 if latest else 1,
        kind=kind, actor_id=actor.id, evidence=evidence)
    db.add(event)
    db.flush()
    db.add(AuditLog(actor_id=actor.id, action="g8_task_" + kind,
        resource_type="g8_analysis_task_event", resource_id=event.id,
        details={"task_id": task.id, "version": event.version,
                 "task_fingerprint": task.fingerprint}))
    db.commit()
    return event

def test_task(db, actor, task_id):
    _authorize(db, actor, "intelligence.studio.test")
    task = _task(db, actor, task_id, lock=True)
    previous = _last_event(db, task)
    if previous is not None:
        raise IntelligenceBlocked("only draft task versions may be tested")
    result = _verified_test(task.configuration)
    evidence = {"task_fingerprint": task.fingerprint, "test": result,
                "test_digest": digest({"task": task.fingerprint, "test": result})}
    return _append_event(db, actor, task, "tested", evidence, previous)

def activate_task(db, actor, task_id):
    _authorize(db, actor, "intelligence.studio.activate")
    task = _task(db, actor, task_id, lock=True)
    previous = _last_event(db, task)
    if previous is None or previous.kind != "tested":
        raise IntelligenceBlocked("T19: only a passing tested task can activate")
    if actor.id in {task.created_by, previous.actor_id}:
        raise IntelligenceBlocked("independent human reviewer required")
    # Verify persisted server-generated evidence, not user-provided success flags.
    expected = _verified_test(task.configuration)
    expected_digest = digest({"task": task.fingerprint, "test": expected})
    if (previous.evidence.get("test_digest") != expected_digest
        or previous.evidence.get("task_fingerprint") != task.fingerprint):
        raise IntelligenceBlocked("synthetic test evidence mismatch")
    versions = db.scalars(select(AnalysisTaskVersion).where(
        AnalysisTaskVersion.organization_id == task.organization_id,
        AnalysisTaskVersion.code == task.code)).all()
    for other in versions:
        if other.id != task.id and task_status(db, other) == "activated":
            raise IntelligenceBlocked("another version is active; deactivate it first")
    return _append_event(db, actor, task, "activated",
        {"test_event_id": previous.id, "test_digest": expected_digest,
         "configuration_fingerprint": task.fingerprint,
         "review_only": True}, previous)

def deactivate_task(db, actor, task_id):
    _authorize(db, actor, "intelligence.studio.activate")
    task = _task(db, actor, task_id, lock=True)
    previous = _last_event(db, task)
    if previous is None or previous.kind != "activated":
        raise IntelligenceBlocked("only active versions may be deactivated")
    return _append_event(db, actor, task, "deactivated",
        {"previous_event_id": previous.id, "reason": "task_version_retired"}, previous)

def _source_rows(db, actor, report_ids):
    if (not isinstance(report_ids, list) or not 1 <= len(report_ids) <= 12
        or len(report_ids) != len(set(report_ids))
        or any(type(item) is not str or not item or len(item) > 36 for item in report_ids)):
        raise IntelligenceBlocked("one to twelve distinct source report IDs required")
    reports = db.scalars(select(ReportSnapshot).where(
        ReportSnapshot.organization_id == actor.organization_id,
        ReportSnapshot.id.in_(report_ids))).all()
    if len(reports) != len(report_ids):
        raise IntelligenceBlocked("G7 source report not accessible")
    reports_by_id = {item.id: item for item in reports}
    reports = [reports_by_id[item] for item in report_ids]
    claim_ids = [entry["claim_id"] for report in reports
                 for entry in report.dataset.get("rows", [])]
    if len(claim_ids) > 10000:
        raise IntelligenceBlocked("G8 cohort larger than approved engineering limit")
    claims = db.scalars(select(ClaimEntry).where(
        ClaimEntry.organization_id == actor.organization_id,
        ClaimEntry.id.in_(claim_ids))).all()
    return assemble(reports, {item.id: item for item in claims})

def create_run(db, actor, kind, report_ids, parameters=None, task_id=None):
    _authorize(db, actor, "intelligence.run")
    _authorize(db, actor, "reports.read")
    if kind not in BUILTIN_KINDS or type(parameters) is not dict:
        raise IntelligenceBlocked("unsupported analysis request")
    if kind != "signals" and task_id is not None:
        raise IntelligenceBlocked("custom task can only create review signals")
    if kind == "signals":
        if task_id is None or parameters:
            raise IntelligenceBlocked("signals require a stored activated Studio task")
        task = _task(db, actor, task_id, lock=True)
        if task_status(db, task) != "activated":
            raise IntelligenceBlocked("T19: untested or inactive Studio task cannot run")
        params = task.configuration
    else:
        task = None
        if kind == "summary":
            if not set(parameters) <= {"dimension", "min_group_size"}:
                raise IntelligenceBlocked("unsupported summary parameter")
            params = {"dimension": parameters.get("dimension", "provider"),
                      "min_group_size": parameters.get("min_group_size", 5)}
        else:
            if set(parameters) != {"reduction_percent"}:
                raise IntelligenceBlocked("explicit simulation assumption required")
            params = dict(parameters)
    rows, sources = _source_rows(db, actor, report_ids)
    if kind == "summary":
        output = aggregate(rows, params["dimension"], params["min_group_size"])
    elif kind == "signals":
        output = signals(rows, params)
    else:
        output = simulate(rows, params["reduction_percent"])
    result = {"analysis_type": kind, "status": "review_only",
              "input_claim_count": len(rows), "output": output,
              "sources": sources, "source": SOURCE,
              "no_automatic_medical_or_financial_decision": True}
    fp = digest({"kind": kind, "sources": sources,
                 "parameters": params, "result": result,
                 "task_id": task.id if task else None})
    run = AnalysisRun(organization_id=actor.organization_id,
        kind=kind, task_id=task.id if task else None,
        sources=sources, parameters=params, result=result,
        fingerprint=fp, created_by=actor.id)
    db.add(run)
    db.flush()
    db.add(AuditLog(actor_id=actor.id, action="g8_analysis_review_created",
        resource_type="g8_analysis_run", resource_id=run.id,
        details={"kind": kind, "sources": [s["report_id"] for s in sources],
                 "fingerprint": fp, "task_id": task.id if task else None}))
    db.commit()
    return run

def verify_run(run):
    expected = digest({"kind": run.kind, "sources": run.sources,
        "parameters": run.parameters, "result": run.result, "task_id": run.task_id})
    if run.fingerprint != expected:
        raise IntelligenceBlocked("G8 historical analysis result integrity mismatch")
    return True
