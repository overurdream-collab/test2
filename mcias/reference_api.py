"""Tenant-scoped reference read and impact-review API."""
from datetime import date
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.tenant import require_organization
from mcias.models_reference import ContractVersion, ProviderTariff, BeneficiaryCategory, BeneficiaryEnrollment
from mcias.reference import analyze_retroactive, active_contract, ReferenceConflict

router = APIRouter(prefix="/api/v1/reference", tags=["reference"])

@router.get("/contracts/{contract_id}/impact")
def contract_impact(contract_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, _ = resolve_user(db, authorization)
    contract = db.get(ContractVersion, contract_id)
    if contract is None:
        raise HTTPException(404, "contract not found")
    require_organization(db, user, contract.organization_id, "reference.read")
    return {"contract_id": contract.id, **analyze_retroactive(db, contract, date.today())}

@router.get("/contracts/active/{provider_code}")
def contract_at(provider_code: str, at: date, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, _ = resolve_user(db, authorization)
    if not user.organization_id:
        raise HTTPException(403, "organization required")
    require_organization(db, user, user.organization_id, "reference.read")
    try:
        contract = active_contract(db, user.organization_id, provider_code, at)
    except ReferenceConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    if contract is None:
        raise HTTPException(404, "no approved contract")
    return {"id": contract.id, "provider_code": contract.provider_code, "version": contract.version,
            "effective_from": contract.effective_from, "effective_until": contract.effective_until}

from pydantic import BaseModel, Field
from decimal import Decimal
from mcias.reference_service import (
    create_draft, add_tariff, create_category, enroll, eligibility,
    attach_authorization, impact_review, approve_precedence_policy,
)
from mcias.reference import approve_contract

class DraftIn(BaseModel):
    provider_code: str = Field(min_length=1, max_length=80)
    effective_from: date
    effective_until: date
    precedence: int = Field(default=0, ge=0, le=10000)

class TariffIn(BaseModel):
    service_code: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)

class CategoryIn(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)

class EnrollmentIn(BaseModel):
    beneficiary_token: str = Field(min_length=1, max_length=128)
    category_id: str
    effective_from: date
    effective_until: date

class AuthorizationIn(BaseModel):
    authorization_id: str

class ReviewIn(BaseModel):
    rationale: str = Field(min_length=20, max_length=2000)

def _effective_permission(db,user,permission):
    # Explicit contract-approval code compatibility, within the same group authority.
    if permission == 'reference.approve':
        from mcias.services.authorization_service import check_permission_unified
        if check_permission_unified(db,user,'reference.contracts.approve'):
            return 'reference.contracts.approve'
    return permission

def _actor(db, authorization, permission):
    user, _ = resolve_user(db, authorization)
    if not user.organization_id:
        raise HTTPException(403, "organization required")
    require_organization(db, user, user.organization_id, _effective_permission(db,user,permission))
    return user

def _contract(db, user, contract_id, permission):
    contract = db.get(ContractVersion, contract_id)
    if contract is None:
        raise HTTPException(404, "contract not found")
    require_organization(db, user, contract.organization_id, _effective_permission(db,user,permission))
    return contract

def _perform(db, operation):
    try:
        return operation()
    except ReferenceConflict as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    except __import__("sqlalchemy").exc.IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "reference constraint violation") from exc

@router.post("/contracts", status_code=201)
def create_contract(payload: DraftIn, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = _actor(db, authorization, "reference.write")
    contract = _perform(db, lambda: create_draft(db, user, payload.provider_code,
                         payload.effective_from, payload.effective_until, payload.precedence))
    return {"id": contract.id, "version": contract.version, "status": contract.status}

@router.post("/contracts/{contract_id}/tariffs", status_code=201)
def create_tariff(contract_id: str, payload: TariffIn, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = _actor(db, authorization, "reference.write")
    _contract(db, user, contract_id, "reference.write")
    tariff = _perform(db, lambda: add_tariff(db, user, contract_id, payload.service_code,
                                             payload.amount, payload.currency))
    return {"id": tariff.id, "contract_id": tariff.contract_id, "amount": str(tariff.amount)}

@router.post("/categories", status_code=201)
def add_category(payload: CategoryIn, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = _actor(db, authorization, "reference.write")
    category = _perform(db, lambda: create_category(db, user, payload.code, payload.description))
    return {"id": category.id, "code": category.code}

@router.post("/enrollments", status_code=201)
def add_enrollment(payload: EnrollmentIn, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = _actor(db, authorization, "reference.write")
    enrollment = _perform(db, lambda: enroll(db, user, payload.beneficiary_token, payload.category_id,
                                             payload.effective_from, payload.effective_until))
    return {"id": enrollment.id, "category_id": enrollment.category_id}

@router.get("/eligibility/{beneficiary_token}")
def beneficiary_eligibility(beneficiary_token: str, at: date,
                            authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = _actor(db, authorization, "reference.read")
    enrollment = _perform(db, lambda: eligibility(db, user.organization_id, beneficiary_token, at))
    return {"eligible": enrollment is not None,
            "category_id": enrollment.category_id if enrollment else None}

@router.post("/contracts/{contract_id}/authorization")
def link_authorization(contract_id: str, payload: AuthorizationIn,
                       authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = _actor(db, authorization, "reference.approve")
    _contract(db, user, contract_id, "reference.approve")
    contract = _perform(db, lambda: attach_authorization(db, user, contract_id, payload.authorization_id))
    return {"id": contract.id, "authorization_attached": True}

@router.post("/contracts/{contract_id}/precedence-review")
def precedence_review(contract_id: str, payload: ReviewIn,
                      authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = _actor(db, authorization, "reference.approve")
    _contract(db, user, contract_id, "reference.approve")
    return _perform(db, lambda: approve_precedence_policy(db, user, contract_id, payload.rationale))

@router.post("/contracts/{contract_id}/impact-review")
def submit_impact_review(contract_id: str, payload: ReviewIn,
                         authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = _actor(db, authorization, "reference.approve")
    _contract(db, user, contract_id, "reference.approve")
    return _perform(db, lambda: impact_review(db, user, contract_id, payload.rationale))

@router.post("/contracts/{contract_id}/approve")
def activate_contract(contract_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = _actor(db, authorization, "reference.approve")
    _contract(db, user, contract_id, "reference.approve")
    return _perform(db, lambda: approve_contract(db, contract_id, user, date.today(),
                                                   precedence_approved=True))

@router.post("/contracts/{contract_id}/tariffs/import")
async def import_tariffs(contract_id: str, request: Request, apply: bool = False,
                         authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    from mcias.tariff_import import preview_csv, TariffImportError
    from mcias.reference_service import apply_tariff_batch
    user = _actor(db, authorization, "reference.write")
    _contract(db, user, contract_id, "reference.write")
    buffer = bytearray()
    async for chunk in request.stream():
        if len(buffer) + len(chunk) > 2_000_000:
            raise HTTPException(413, "tariff CSV exceeds 2 MB")
        buffer.extend(chunk)
    try:
        preview = preview_csv(bytes(buffer))
    except TariffImportError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not apply:
        return preview
    if not preview["complete"] or not preview["accepted"]:
        raise HTTPException(409, "all tariff rows must validate before atomic import")
    return _perform(db, lambda: apply_tariff_batch(db, user, contract_id, preview["accepted"]))
