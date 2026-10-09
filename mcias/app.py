from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from mcias.config import Settings
from mcias.auth import authenticate, resolve_user, revoke_session, require_permission
from mcias.governance import activate_rule, exclusion_edit_permission
from mcias.mfa_enrollment import begin_enrollment, confirm_enrollment
from mcias.security import verify_password

app = FastAPI(title="MCIAS API", version="0.1.0")

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
def login(payload: LoginRequest, db: Session = Depends(get_db)):
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
def mfa_enroll(payload: MFAEnrollRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, session = resolve_user(db, authorization)
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return begin_enrollment(db, user)

@app.post("/api/v1/auth/mfa/confirm")
def mfa_confirm(payload: MFAConfirmRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user, session = resolve_user(db, authorization)
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return confirm_enrollment(db, user, payload.code)
