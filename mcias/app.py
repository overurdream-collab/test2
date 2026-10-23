import os
from fastapi import FastAPI, HTTPException, Header, Depends, Response, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from mcias.config import Settings
from mcias.auth import authenticate, resolve_user, revoke_session, require_permission
from mcias.governance import activate_rule, exclusion_edit_permission
from mcias.mfa_enrollment import begin_enrollment, confirm_enrollment
from mcias.security import verify_password
from mcias.tenant import require_organization, require_sensitive_field
from mcias.models import RuleVersion

app = FastAPI(
    title="MCIAS API",
    version="0.1.0",
    docs_url=None if os.environ.get("MCIAS_ENVIRONMENT") == "production" else "/docs",
    redoc_url=None if os.environ.get("MCIAS_ENVIRONMENT") == "production" else "/redoc",
    openapi_url=None if os.environ.get("MCIAS_ENVIRONMENT") == "production" else "/openapi.json",
)

from mcias.rate_limits import rate_limit_middleware
app.middleware("http")(rate_limit_middleware)
from mcias.middleware.features import feature_middleware
app.middleware("http")(feature_middleware)

@app.middleware("http")
async def secure_response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    if request.url.path.startswith(("/ui/reports", "/ui/intelligence", "/admin", "/institution", "/shared", "/login", "/mfa", "/forgot-password", "/workspace-assets")):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; font-src 'self'; img-src 'self'; "
            "base-uri 'none'; form-action 'self'; object-src 'none'; "
            "frame-ancestors 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if request.url.path.startswith(("/api/v1/auth/", "/api/v1/reports/", "/api/v1/governance/", "/api/v1/audits/",
                                        "/api/v1/users", "/api/v1/groups", "/api/v1/permissions", "/api/v1/rbac/",
                                        "/api/v1/rules/", "/api/v1/workspace/", "/api/v1/claims/", "/api/v1/ingestion/", "/api/v1/reference/", "/api/v1/audit-policies/", "/api/v1/report-explorer/", "/api/v1/intelligence/", "/ui/reports", "/ui/intelligence")):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=1024)
    totp_code: str | None = Field(default=None, min_length=6, max_length=6)

def get_settings():
    return Settings()

def get_db(settings: Settings = Depends(get_settings)):
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()

def get_rate_limit_db():
    yield from get_db(get_settings())

@app.get("/health/live")
def live():
    return {"status": "ok"}

@app.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ready"}

@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return {"access_token": authenticate(db, payload.username, payload.password, payload.totp_code), "token_type": "bearer", "expires_in": 1800}

@app.post("/api/v1/auth/logout", status_code=204)
def logout(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, session = resolve_user(db, authorization)
    revoke_session(db, session)

@app.get("/api/v1/auth/me")
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, session = resolve_user(db, authorization)
    require_permission(db, user, "profile.read")
    return {"id": user.id, "username": user.username, "organization_id": user.organization_id}

@app.get("/api/v1/system/status")
def system_status(x_bootstrap_token: str | None = Header(default=None), settings: Settings = Depends(get_settings)):
    if settings.environment != "development" or not settings.bootstrap_token or x_bootstrap_token != settings.bootstrap_token:
        raise HTTPException(status_code=403, detail="forbidden")
    return {"version": "0.1.0", "phase": "G1", "production_ready": False}

@app.post("/api/v1/rules/{rule_id}/activate")
def activate_rule_api(rule_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, session = resolve_user(db, authorization)
    return activate_rule(db, user, rule_id)

@app.get("/api/v1/rules/exclusions/edit-permission")
def exclusion_edit_permission_api(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, session = resolve_user(db, authorization)
    return exclusion_edit_permission(db, user)

class MFAEnrollRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)

class MFAConfirmRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")

@app.post("/api/v1/auth/mfa/enroll")
def mfa_enroll(payload: MFAEnrollRequest, response: Response, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, session = resolve_user(db, authorization)
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return begin_enrollment(db, user)

@app.post("/api/v1/auth/mfa/confirm")
def mfa_confirm(payload: MFAConfirmRequest, response: Response, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, session = resolve_user(db, authorization)
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return confirm_enrollment(db, user, payload.code)

@app.get("/api/v1/rules/{rule_id}")
def rule_details(rule_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, _ = resolve_user(db, authorization)
    rule = db.get(RuleVersion, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    require_organization(db, user, rule.organization_id, "rules.read")
    return {"id": rule.id, "rule_type": rule.rule_type, "status": rule.status}

@app.get("/api/v1/organizations/{organization_id}/sensitive-fields/{field_code}/access")
def sensitive_field_access(organization_id: str, field_code: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, _ = resolve_user(db, authorization)
    require_sensitive_field(db, user, organization_id, field_code)
    return {"allowed": True}

# Import after get_db is defined to avoid a dependency cycle during route registration.
from mcias.ingestion.api import router as ingestion_router
app.include_router(ingestion_router)

from mcias.reference_api import router as reference_router
app.include_router(reference_router)

from mcias.claims_api import router as claims_router
app.include_router(claims_router)

from mcias.audit_api import router as audit_router
app.include_router(audit_router)

from mcias.audit_policy_api import router as audit_policy_router
app.include_router(audit_policy_router)

from mcias.governance_g6_api import router as governance_g6_router
app.include_router(governance_g6_router)

from mcias.reporting_g7_api import router as reporting_g7_router
app.include_router(reporting_g7_router)

from mcias.reporting_g7_explorer import router as reporting_g7_explorer_router
app.include_router(reporting_g7_explorer_router)

from mcias.report_web_g7 import router as report_web_g7_router
app.include_router(report_web_g7_router)

from mcias.intelligence_g8_api import router as intelligence_g8_router
app.include_router(intelligence_g8_router)

from mcias.report_web_g8 import router as report_web_g8_router
app.include_router(report_web_g8_router)

from mcias.workspace_api import router as workspace_api_router
app.include_router(workspace_api_router)
from mcias.workspace_web import router as workspace_web_router
app.include_router(workspace_web_router)

from mcias.retention_api import router as retention_router
app.include_router(retention_router)

from mcias.api.features_routes import router as features_router
app.include_router(features_router, prefix="/api/v1")
from mcias.api.feature_data_routes import router as feature_data_router
app.include_router(feature_data_router)
from mcias.api.registry_routes import router as registry_router
app.include_router(registry_router)

from mcias.api.users_routes import router as rbac_users_router
from mcias.api.groups_routes import router as rbac_groups_router
from mcias.api.permissions_routes import router as rbac_permissions_router
from mcias.api.seed_routes import router as rbac_seed_router
from mcias.middleware.audit import AuditMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler

for router in (rbac_users_router, rbac_groups_router, rbac_permissions_router, rbac_seed_router):
    app.include_router(router)
app.add_middleware(AuditMiddleware)

@app.exception_handler(RequestValidationError)
async def safe_rbac_validation(request: Request, exc: RequestValidationError):
    if request.url.path.startswith(("/api/v1/users", "/api/v1/groups", "/api/v1/permissions", "/api/v1/rbac/", "/api/v1/admin/features", "/api/v1/admin/rbac/", "/api/v1/organizations/", "/api/v1/me/features", "/api/v1/registry/", "/api/v1/institution/")):
        return JSONResponse(status_code=422, content={"detail": [
            {key: error[key] for key in ("loc", "msg", "type") if key in error}
            for error in exc.errors()
        ]})
    return await request_validation_exception_handler(request, exc)

from mcias.api.rbac_provisioning_routes import router as rbac_provisioning_router
app.include_router(rbac_provisioning_router)

from mcias.api.institution_routes import router as institution_router
app.include_router(institution_router)

from mcias.api.access_routes import router as access_router
app.include_router(access_router)

from mcias.api.result_routes import router as result_files_router
app.include_router(result_files_router)
