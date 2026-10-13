"""Bounded, read-only workspace projections. No financial engine or policy changes.

Every projection uses the existing tenant and permission guards. Global technical
administration additionally requires the super_admin role; no implicit grants.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.app import get_db
from mcias.auth import resolve_user, require_permission
from mcias.tenant import require_organization
from mcias.models import Organization, User, Role, UserRole
from mcias.models_claims import ClaimBatch, ClaimEntry
from mcias.models_ingestion import IngestionDocument, IngestionJob
from mcias.models_reference import ContractVersion
from mcias.models_audit import AuditSnapshot
from mcias.models_governance_g6 import GovernanceCase

router = APIRouter(prefix="/api/v1/workspace", tags=["workspace read models"])

def role_codes(db, actor):
    return list(db.scalars(select(Role.code).join(UserRole).where(UserRole.user_id == actor.id)).all())

@router.get("/context")
def context(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    actor, session = resolve_user(db, authorization)
    require_permission(db, actor, "profile.read")
    organization = db.get(Organization, actor.organization_id) if actor.organization_id else None
    from mcias.services.authorization_service import permission_codes
    permissions = permission_codes(db,actor)
    return {"id": actor.id, "username": actor.username,
            "organization": {"id": organization.id, "name": organization.name} if organization else None,
            "roles": role_codes(db, actor), "permissions": sorted(permissions),
            "expires_at": session.expires_at, "institutionally_accepted": False,
            "tenant_switching": False}

# Only explicitly approved fields are serialized; never raw medical source values.
CATALOG = {
    "batches": (ClaimBatch, "claims.read", ("id", "status", "record_count", "imported_count", "source_sha256", "created_at")),
    "claims": (ClaimEntry, "claims.read", ("id", "batch_id", "claim_reference", "service_date", "claimed_amount", "currency")),
    "documents": (IngestionDocument, "ingestion.read", ("id", "status", "sha256", "revision_of", "created_at")),
    "jobs": (IngestionJob, "ingestion.read", ("id", "document_id", "status", "created_at")),
    "contracts": (ContractVersion, "reference.read", ("id", "provider_code", "version", "status", "effective_from", "effective_until")),
    "audits": (AuditSnapshot, "claims.read", ("id", "claim_id", "policy_id", "policy_fingerprint", "created_at")),
    "cases": (GovernanceCase, "claims.read", ("id", "claim_id", "audit_snapshot_id", "created_at")),
    "users": (User, "users.read", ("id", "username", "active", "created_at")),
}

@router.get("/catalog/{kind}")
def catalog(kind: str, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0),
            authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    actor, _ = resolve_user(db, authorization)
    if kind not in CATALOG:
        raise HTTPException(404, "unsupported catalog")
    model, permission, fields = CATALOG[kind]
    require_organization(db, actor, actor.organization_id, permission)
    query = select(model).where(model.organization_id == actor.organization_id)
    order = [model.created_at.desc(), model.id.desc()] if hasattr(model, "created_at") else [model.id]
    records = db.scalars(query.order_by(*order).offset(offset).limit(limit + 1)).all()
    items = []
    for record in records[:limit]:
        item = {field: getattr(record, field) for field in fields}
        if "claimed_amount" in item:
            item["claimed_amount"] = str(item["claimed_amount"])
        items.append(item)
    return {"items": items, "has_more": len(records) > limit, "offset": offset,
            "limit": limit, "retrieved_at": datetime.now(timezone.utc),
            "scope": "current_organization", "institutionally_accepted": False}

@router.get("/claims/{claim_id}")
def claim_detail(claim_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    actor, _ = resolve_user(db, authorization)
    require_organization(db, actor, actor.organization_id, "claims.read")
    claim = db.scalar(select(ClaimEntry).where(ClaimEntry.id == claim_id, ClaimEntry.organization_id == actor.organization_id))
    if claim is None:
        raise HTTPException(404, "claim not found")
    return {field: str(getattr(claim, field)) for field in CATALOG["claims"][2]}

@router.get('/demo-availability')
def demo_availability():
    import os
    from mcias.config import Settings
    try:
        enabled = Settings().environment == 'development' and os.getenv('MCIAS_ENABLE_UI_DEMO') == 'true'
    except ValueError:
        enabled = False
    return {'enabled': enabled}

@router.get('/users/{user_id}')
def user_detail(user_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    actor, _ = resolve_user(db, authorization)
    require_organization(db, actor, actor.organization_id, 'users.read')
    user = db.scalar(select(User).where(User.id == user_id, User.organization_id == actor.organization_id))
    if user is None:
        raise HTTPException(404, 'user not found')
    return {field: getattr(user, field) for field in CATALOG['users'][2]}
