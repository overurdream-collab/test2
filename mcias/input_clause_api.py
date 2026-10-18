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

# Bounded contract-only adapter of existing persisted G2 page text.
# It is not an LLM and refuses unknown document layouts rather than guessing.
import re
from datetime import date as _date
from sqlalchemy import select as _select
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord
from mcias.tenant import require_sensitive_field

_SYN_CLAUSE = re.compile(r"Service\s+([A-Za-z0-9_.:-]{1,100})\s+Price\s+(\d+(?:\.\d{1,4})?)\s+([A-Z]{3})\s+effective\s+(\d{4}-\d{2}-\d{2})", re.I)

def _contract_candidates(db, user, document_id):
    document = db.get(IngestionDocument, document_id)
    if not document or document.organization_id != user.organization_id:
        raise HTTPException(404, "source missing")
    if document.status != "extracted":
        raise HTTPException(409, "source not verified by G2")
    job = db.scalar(_select(IngestionJob).where(IngestionJob.document_id == document.id,
        IngestionJob.organization_id == user.organization_id).order_by(IngestionJob.created_at.desc()))
    if not job or job.status != "extracted" or not job.manifest.get("complete"):
        raise HTTPException(409, "G2 extraction incomplete")
    rows = db.scalars(_select(ExtractedSourceRecord).where(ExtractedSourceRecord.job_id == job.id).limit(41)).all()
    if not rows or len(rows) > 40:
        raise HTTPException(409, "invalid extraction size")
    items = []
    for row in rows:
        for key, value in row.values.items():
            require_sensitive_field(db, user, user.organization_id, key)
            if key != "text" or not isinstance(value, str):
                continue
            for match in _SYN_CLAUSE.finditer(value):
                service, amount, currency, effective = match.groups()
                try:
                    _date.fromisoformat(effective)
                except ValueError:
                    continue
                items.append({"type":"amount","service_code":service,"value":amount,"currency":currency,
                    "effective_from":effective,"source_record_id":row.id,"source_locator":row.locator,
                    "original_quote":match.group(0),"original_value":amount})
    if len(items) != 1:
        raise HTTPException(409, "only one unambiguous synthetic contract term supported")
    return items[0]

@router.get("/contracts/documents/{document_id}/preview")
def preview_contract_document(document_id: str, authorization: str | None = Header(default=None),
                              db: Session = Depends(get_db)):
    user = _user(db, authorization, "reference.write")
    item = _contract_candidates(db, user, document_id)
    return {"status":"REVIEW_REQUIRED","document_id":document_id,"clauses":[item]}

class ConfirmContract(BaseModel):
    source_record_id: str
    service_code: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")
    corrected_value: str = Field(pattern=r"^\d+(?:\.\d{1,4})?$")
    effective_from: date
    human_confirmed: bool = False

@router.post("/contracts/documents/{document_id}/confirm", status_code=201)
def confirm_contract_document(document_id: str, payload: ConfirmContract,
                              authorization: str | None = Header(default=None),
                              db: Session = Depends(get_db)):
    user = _user(db, authorization, "reference.write")
    if not payload.human_confirmed:
        raise HTTPException(409, "explicit human confirmation required")
    original = _contract_candidates(db, user, document_id)
    if payload.source_record_id != original["source_record_id"] or payload.service_code != original["service_code"]:
        raise HTTPException(409, "source identity mismatch")
    if payload.effective_from.isoformat() != original["effective_from"]:
        raise HTTPException(409, "unverified effective date")
    from decimal import Decimal
    corrected = Decimal(payload.corrected_value)
    if not corrected.is_finite() or corrected < 0 or corrected >= Decimal("100000000000000"):
        raise HTTPException(422, "invalid correction")
    data = {"type":"amount","service_code":original["service_code"],
            "amount":payload.corrected_value,"currency":original["currency"],
            "original_amount":original["original_value"],"original_quote":original["original_quote"],
            "human_confirmed":True}
    item = _guard(lambda: create_draft(db, user, section="contracts",
        logical_key=original["service_code"], clause_text=original["original_quote"],
        structured_value=data, effective_from=payload.effective_from,
        source_document_id=document_id, source_locator=original["source_locator"]))
    return {"id":item.id,"status":"draft","version":item.version}
