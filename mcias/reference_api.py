"""Tenant-scoped reference read and impact-review API."""
from datetime import date
from fastapi import APIRouter, Depends, Header, HTTPException
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
