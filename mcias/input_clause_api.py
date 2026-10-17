"""Tenant-scoped, review-gated historical insurance clause registry."""
from datetime import date
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.models_input_clauses import InputClause, SECTIONS
from mcias.input_clause_service import (InputClauseError, create_draft, list_points,
                                        authorize_draft, at_date, public_point, _events)

router = APIRouter(prefix="/api/v1/input-clauses", tags=["Input clause registry"])

class NewClause(BaseModel):
    section: str
    logical_key: str = Field(min_length=1, max_length=100)
    clause_text: str = Field(min_length=3, max_length=2000)
    structured_value: dict = Field(default_factory=dict)
    provider_code: str = Field(default="", max_length=80)
    insurer_code: str = Field(default="", max_length=80)
    effective_from: date
    effective_until: date | None = None
    source_document_id: str | None = None
    source_locator: dict = Field(default_factory=dict)
    replaces_id: str | None = None

class ActivateClause(BaseModel):
    authorization_id: str = Field(min_length=1, max_length=36)

def _user(db, authorization, permission):
    user, _ = resolve_user(db, authorization)
    require_organization(db, user, user.organization_id, permission)
    return user

def _guard(callback):
    try:
        return callback()
    except InputClauseError as e:
        raise HTTPException(409, str(e)) from e

@router.get("/sections")
def sections(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    _user(db, authorization, "reference.read")
    return {"sections": list(SECTIONS), "production_activation": False,
            "notice": "Sections are draft evidence catalogs, not live financial policy for G5."}

@router.get("/sections/{section}")
def section_points(section: str, limit: int = Query(50, ge=1, le=100),
                   offset: int = Query(0, ge=0), provider_code: str | None = None,
                   at: date | None = None, authorization: str | None = Header(default=None),
                   db: Session = Depends(get_db)):
    user = _user(db, authorization, "reference.read")
    return {"items": _guard(lambda: list_points(db, user, section, limit=limit, offset=offset,
                                                  at=at, provider_code=provider_code)),
            "limit": limit, "offset": offset, "section": section}

@router.get("/points/{point_id}")
def point_details(point_id: str, authorization: str | None = Header(default=None),
                  db: Session = Depends(get_db)):
    user = _user(db, authorization, "reference.read")
    item = db.get(InputClause, point_id)
    if item is None or item.organization_id != user.organization_id:
        raise HTTPException(404, "clause not found")
    return public_point(item, _events(db, [item.id])[item.id])

@router.get("/resolve/{section}/{logical_key}")
def resolve_point(section: str, logical_key: str, on: date,
                  provider_code: str = "", insurer_code: str = "",
                  authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = _user(db, authorization, "reference.read")
    result = _guard(lambda: at_date(db, user, section=section, logical_key=logical_key,
                                    provider_code=provider_code, insurer_code=insurer_code, on=on))
    if result is None:
        raise HTTPException(404, "no approved clause for date and scope")
    return result

@router.post("/points", status_code=201)
def new_point(payload: NewClause, authorization: str | None = Header(default=None),
              db: Session = Depends(get_db)):
    user = _user(db, authorization, "reference.write")
    item = _guard(lambda: create_draft(db, user, **payload.model_dump()))
    return {"id": item.id, "version": item.version, "status": "draft",
            "notice": "Draft only; source extraction and G3 policy linkage are not automated."}

@router.post("/points/{point_id}/activate")
def activate_point(point_id: str, payload: ActivateClause,
                   authorization: str | None = Header(default=None),
                   db: Session = Depends(get_db)):
    user = _user(db, authorization, "reference.approve")
    return _guard(lambda: authorize_draft(db, user, point_id, payload.authorization_id))
