"""G8 authenticated intelligence & Analysis Studio APIs. Nothing here settles a claim."""
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.models_g8 import AnalysisTaskVersion, AnalysisTaskEvent, AnalysisRun
from mcias.intelligence_g8 import IntelligenceBlocked, SOURCE, DIMENSIONS, INDICATORS
from mcias.intelligence_service_g8 import (
    create_task, test_task, activate_task, deactivate_task, task_status,
    create_run, verify_run,
)

router = APIRouter(prefix="/api/v1/intelligence", tags=["G8 intelligence"])

class NewTask(BaseModel):
    code: str = Field(min_length=3, max_length=64, pattern=r"^[a-z][a-z0-9_]+$")
    configuration: dict

class RunRequest(BaseModel):
    kind: Literal["summary", "signals", "simulation"]
    report_ids: list[str] = Field(min_length=1, max_length=12)
    parameters: dict = Field(default_factory=dict)
    task_id: str | None = None

def _actor(db, authorization, permission):
    user, _ = resolve_user(db, authorization)
    if not user.organization_id:
        raise HTTPException(403, "organization required")
    require_organization(db, user, user.organization_id, permission)
    return user

def _execute(db, action):
    try:
        return action()
    except IntelligenceBlocked as exc:
        db.rollback()
        detail = str(exc)
        if "not accessible" in detail or "missing" == detail:
            code = 404
        elif "permission denied" in detail:
            code = 403
        elif any(x in detail for x in ("T19", "inactive", "test evidence",
            "version is active", "another version is active", "only draft",
            "only active", "human reviewer", "historical analysis", "integrity",
            "do not", "cannot", "provenance mismatch")):
            code = 409
        else:
            code = 422
        raise HTTPException(code, detail) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "G8 database uniqueness or integrity constraint") from exc

def _task_details(db, task):
    return {"id": task.id, "code": task.code, "version": task.version,
            "configuration": task.configuration,
            "configuration_fingerprint": task.fingerprint,
            "status": task_status(db, task)}

def _event_details(event):
    return {"id": event.id, "version": event.version,
            "kind": event.kind, "task_id": event.task_id,
            "evidence": event.evidence}

def _run_details(run):
    return {"id": run.id, "kind": run.kind, "task_id": run.task_id,
            "sources": run.sources, "parameters": run.parameters,
            "fingerprint": run.fingerprint, "result": run.result}

@router.get("/capabilities")
def capabilities(authorization: str | None = Header(default=None),
                 db: Session = Depends(get_db)):
    _actor(db, authorization, "intelligence.read")
    return {"source": SOURCE, "dimensions": sorted(DIMENSIONS),
            "indicators": sorted(INDICATORS), "minimum_privacy_group": 5,
            "review_only": True, "no_external_ai": True,
            "no_automatic_financial_or_clinical_decisions": True}

@router.post("/studio/tasks", status_code=201)
def add_task(body: NewTask, authorization: str | None = Header(default=None),
             db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "intelligence.studio.manage")
    return _execute(db, lambda: _task_details(
        db, create_task(db, actor, body.code, body.configuration)))

@router.get("/studio/tasks")
def tasks(limit: int = Query(50, ge=1, le=100),
          offset: int = Query(0, ge=0),
          authorization: str | None = Header(default=None),
          db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "intelligence.studio.read")
    rows = db.scalars(select(AnalysisTaskVersion).where(
        AnalysisTaskVersion.organization_id == actor.organization_id
    ).order_by(AnalysisTaskVersion.created_at.desc(), AnalysisTaskVersion.id.desc()
    ).limit(limit + 1).offset(offset)).all()
    return {"items": [_task_details(db, row) for row in rows[:limit]],
            "has_more": len(rows) > limit}

@router.get("/studio/tasks/{task_id}")
def task_detail(task_id: str, authorization: str | None = Header(default=None),
                db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "intelligence.studio.read")
    task = db.scalar(select(AnalysisTaskVersion).where(
        AnalysisTaskVersion.id == task_id,
        AnalysisTaskVersion.organization_id == actor.organization_id))
    if task is None:
        raise HTTPException(404, "task not found")
    detail = _task_details(db, task)
    events = db.scalars(select(AnalysisTaskEvent).where(
        AnalysisTaskEvent.organization_id == actor.organization_id,
        AnalysisTaskEvent.task_id == task.id
    ).order_by(AnalysisTaskEvent.version)).all()
    detail["events"] = [_event_details(event) for event in events]
    return detail

@router.post("/studio/tasks/{task_id}/test", status_code=201)
def test_draft(task_id: str, authorization: str | None = Header(default=None),
               db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "intelligence.studio.test")
    return _execute(db, lambda: _event_details(test_task(db, actor, task_id)))

@router.post("/studio/tasks/{task_id}/activate", status_code=201)
def activate_tested(task_id: str, authorization: str | None = Header(default=None),
                    db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "intelligence.studio.activate")
    return _execute(db, lambda: _event_details(activate_task(db, actor, task_id)))

@router.post("/studio/tasks/{task_id}/deactivate", status_code=201)
def deactivate(task_id: str, authorization: str | None = Header(default=None),
               db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "intelligence.studio.activate")
    return _execute(db, lambda: _event_details(deactivate_task(db, actor, task_id)))

@router.post("/runs", status_code=201)
def new_run(body: RunRequest, authorization: str | None = Header(default=None),
            db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "intelligence.run")
    return _execute(db, lambda: _run_details(create_run(
        db, actor, body.kind, body.report_ids, body.parameters, body.task_id)))

@router.get("/runs")
def list_runs(limit: int = Query(25, ge=1, le=100),
              offset: int = Query(0, ge=0),
              authorization: str | None = Header(default=None),
              db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "intelligence.read")
    rows = db.scalars(select(AnalysisRun).where(
        AnalysisRun.organization_id == actor.organization_id
    ).order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc()
    ).limit(limit + 1).offset(offset)).all()
    for item in rows:
        _execute(db, lambda obj=item: verify_run(obj))
    return {"items": [{"id": row.id, "kind": row.kind,
                       "fingerprint": row.fingerprint, "task_id": row.task_id,
                       "source_count": len(row.sources)} for row in rows[:limit]],
            "has_more": len(rows) > limit}

@router.get("/runs/{run_id}")
def run_detail(run_id: str, authorization: str | None = Header(default=None),
               db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "intelligence.read")
    run = db.scalar(select(AnalysisRun).where(
        AnalysisRun.id == run_id,
        AnalysisRun.organization_id == actor.organization_id))
    if run is None:
        raise HTTPException(404, "analysis result not found")
    return _execute(db, lambda: _run_details(run) if verify_run(run) else None)
