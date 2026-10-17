"""Disabled-by-default read-only A1 review preview from real G2/G4 records.

No public model, no DB writes, no policy activation, no production access.
The operator must explicitly opt into synthetic engineering verification.
"""
import os
from uuid import uuid4
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from mcias.app import get_db
from mcias.auth import resolve_user
from mcias.storage import EncryptedStore
from mcias.tenant import require_organization
from mcias.agents.a1_trusted_input import (preview_a1_from_g4,
                                            A1AccessDenied, A1SourceBlocked)

router=APIRouter(prefix="/api/v1/a1",tags=["a1-experimental"])

@router.get("/claims/{claim_id}/preview")
def preview_a1_endpoint(claim_id: str,
                        authorization: str | None=Header(default=None),
                        db: Session=Depends(get_db)):
    if os.environ.get("MCIAS_ENVIRONMENT")=="production" or \
       os.environ.get("MCIAS_A1_PREVIEW_ENABLED")!="true":
        raise HTTPException(status_code=503,detail="experimental A1 preview disabled")
    user,_=resolve_user(db,authorization)
    if not getattr(user,"organization_id",None):
        raise HTTPException(status_code=403,detail="organization required")
    require_organization(db,user,user.organization_id,"claims.read")
    try:
        store=EncryptedStore(os.environ["MCIAS_STORAGE_DIR"],
                             bytes.fromhex(os.environ["MCIAS_STORAGE_KEY"]))
    except (KeyError,ValueError):
        raise HTTPException(status_code=503,detail="verified local storage unavailable") from None
    try:
        return preview_a1_from_g4(db,user,claim_id,store,run_id="a1-preview-"+uuid4().hex)
    except A1AccessDenied:
        raise HTTPException(status_code=404,detail="claim not accessible") from None
    except A1SourceBlocked:
        raise HTTPException(status_code=409,detail="trusted A1 source unavailable") from None
