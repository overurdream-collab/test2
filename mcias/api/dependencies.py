from datetime import date
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.exc import DBAPIError, IntegrityError
from mcias.auth import resolve_user
from mcias.services.authorization_service import check_permission_unified
from mcias.services import rbac_service as rbac

def open_db():
    # Deferred import keeps standalone router imports free of app/router cycles.
    from mcias.app import app, get_db as existing_get_db, get_settings
    provider = app.dependency_overrides.get(get_db) or app.dependency_overrides.get(existing_get_db)
    yield from (provider() if provider else existing_get_db(get_settings()))

def get_db():
    yield from open_db()

def require_auth(request: Request, authorization: str | None = Header(default=None), db=Depends(get_db)):
    actor, session = resolve_user(db, authorization)
    if not rbac._live_user(actor, date.today()):
        raise HTTPException(401, "invalid session")
    if not actor.organization_id:
        raise HTTPException(403, "organization context required")
    if rbac._super_role(db, actor) and not rbac._technical_admin(db, actor):
        raise HTTPException(403, "privileged MFA enrollment required")
    request.state.rbac_actor = {
        "id": actor.id, "username": actor.username,
        "organization_id": actor.organization_id, "session_id": session.id,
    }
    request.state.rbac_session_expires_at = session.expires_at
    return actor

def require_permission(*codes):
    def guard(actor=Depends(require_auth), db=Depends(get_db)):
        for code in codes:
            if not check_permission_unified(db, actor, code):
                raise HTTPException(403, "permission denied")
        return actor
    return guard

def require_seed_admin(actor=Depends(require_auth), db=Depends(get_db)):
    if not rbac._technical_admin(db, actor):
        raise HTTPException(403, "existing MFA-enabled super_admin role required")
    return actor

def protect_user(db, actor, user):
    try:
        rbac._protect_user(db, actor, user)
    except ValueError:
        raise HTTPException(403, "privileged account management denied") from None

def delegate(db, actor, codes):
    try:
        rbac._delegate(db, actor, codes, date.today())
    except ValueError:
        raise HTTPException(403, "permission delegation denied") from None

def mutate(db, operation, project):
    """Validate the public result and commit both service data and audit before 2xx."""
    try:
        result = operation()
        response = project(result)
        db.commit()
        return response
    except HTTPException:
        db.rollback()
        raise
    except (ValueError, IntegrityError):
        db.rollback()
        raise HTTPException(409, "operation conflicts with current state") from None
    except DBAPIError:
        db.rollback()
        raise HTTPException(503, "database operation unavailable") from None
    except Exception:
        db.rollback()
        raise
