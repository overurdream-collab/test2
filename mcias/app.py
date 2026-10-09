from fastapi import FastAPI, HTTPException, Header, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from mcias.config import Settings
from mcias.models import AuditLog

app = FastAPI(title="MCIAS API", version="0.1.0")

def get_settings():
    return Settings()

def get_db(settings: Settings = Depends(get_settings)):
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with Session(engine) as session:
        yield session
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

@app.get("/api/v1/system/status")
def system_status(x_bootstrap_token: str | None = Header(default=None), settings: Settings = Depends(get_settings)):
    # Temporary development-only protection; not a replacement for MFA and RBAC.
    if settings.environment != "development" or not settings.bootstrap_token or x_bootstrap_token != settings.bootstrap_token:
        raise HTTPException(status_code=403, detail="forbidden")
    return {"version": "0.1.0", "phase": "G1", "production_ready": False}
