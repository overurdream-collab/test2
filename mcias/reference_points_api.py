"""Tenant and permission-scoped API for independently approved input points."""
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from mcias.app import get_db
from mcias.auth import resolve_user, require_permission
from mcias.tenant import require_organization
from mcias.models_reference_points import ReferencePoint
from mcias.reference_points import PointConflict, MAX_DATE, create_draft, approve, list_points, as_dict, _end

router = APIRouter(prefix="/api/v1/reference-points", tags=["temporal reference points"])


class PointDraft(BaseModel):
    section: str = Field(max_length=32)
    logical_key: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    clause_text: str = Field(min_length=1, max_length=2000)
    rule_type: str = "text"
    provider_code: str | None = Field(default=None, max_length=80)
    service_code: str | None = Field(default=None, max_length=100)
    amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    effective_from: date
    effective_until: date = MAX_DATE
    supersedes_id: str | None = None
    source_document_id: str | None = None
    source_locator: dict | None = None


class Approval(BaseModel):
    authorization_id: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=20, max_length=500)


def _actor(db, authorization, permission):
    actor, _ = resolve_user(db, authorization)
    if not actor.organization_id:
        raise HTTPException(403, "organization required")
    require_organization(db, actor, actor.organization_id, permission)
    return actor


def _safe(db, callback):
    try:
        return callback()
    except (PointConflict, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(409, "reference point conflict" if isinstance(exc, IntegrityError) else str(exc)) from exc


@router.get("")
def list_section(section: str, at: date | None = None,
                 limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0),
                 authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "reference.read")
    items = _safe(db, lambda: list_points(db, actor.organization_id, section, at, limit, offset))
    return {"section": section, "items": items[:limit], "offset": offset, "has_more": len(items) > limit}


@router.post("", status_code=201)
def new_point(payload: PointDraft, authorization: str | None = Header(default=None),
              db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "reference.write")
    require_permission(db, actor, "workspace.super_admin")
    point = _safe(db, lambda: create_draft(db, actor, payload.model_dump()))
    return as_dict(point)


@router.get("/{point_id}")
def detail(point_id: str, authorization: str | None = Header(default=None),
           db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "reference.read")
    point = db.get(ReferencePoint, point_id)
    if not point or point.organization_id != actor.organization_id:
        raise HTTPException(404, "reference point not found")
    return as_dict(point, _end(db, point))


@router.post("/{point_id}/approve")
def activate(point_id: str, payload: Approval, authorization: str | None = Header(default=None),
             db: Session = Depends(get_db)):
    actor = _actor(db, authorization, "reference.approve")
    point = _safe(db, lambda: approve(db, actor, point_id, payload.authorization_id, payload.reason))
    return as_dict(point, _end(db, point))
