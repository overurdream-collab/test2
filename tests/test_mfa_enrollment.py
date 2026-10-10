import base64
import os
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from mcias.app import app, get_db
from mcias.models import Base, User, MFAFactor
from mcias.security import hash_password
from mcias.mfa import generate_totp

def test_mfa_enrollment_flow(monkeypatch):
    monkeypatch.setenv("MCIAS_MFA_ENCRYPTION_KEY", "11" * 32)
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread":False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(username="mfa-test", password_hash=hash_password("synthetic-long-password")))
        db.commit()
    def override():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        login_response = client.post("/api/v1/auth/login", json={"username":"mfa-test","password":"synthetic-long-password"})
        assert login_response.headers["cache-control"] == "no-store"
        token = login_response.json()["access_token"]
        headers = {"Authorization":"Bearer "+token}
        assert client.post("/api/v1/auth/mfa/enroll", headers=headers, json={"current_password":"incorrect"}).status_code == 401
        response = client.post("/api/v1/auth/mfa/enroll", headers=headers, json={"current_password":"synthetic-long-password"})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        secret = base64.b32decode(response.json()["secret_base32"] + "=" * (-len(response.json()["secret_base32"]) % 8))
        with Session(engine) as db:
            factor = db.query(MFAFactor).one()
            assert not factor.enabled
            assert secret not in factor.encrypted_secret
        assert client.post("/api/v1/auth/mfa/confirm", headers=headers, json={"current_password":"synthetic-long-password","code":"not-a-code"}).status_code == 422
        code = generate_totp(secret, int(time.time()) // 30)
        assert client.post("/api/v1/auth/mfa/confirm", headers=headers, json={"current_password":"wrong","code":code}).status_code == 401
        assert client.post("/api/v1/auth/mfa/confirm", headers=headers, json={"current_password":"synthetic-long-password","code":code}).json() == {"enabled":True}
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
        assert client.post("/api/v1/auth/mfa/enroll", headers=headers, json={"current_password":"synthetic-long-password"}).status_code == 401
        assert client.post("/api/v1/auth/login", json={"username":"mfa-test","password":"synthetic-long-password"}).status_code == 401
        next_code = generate_totp(secret, int(time.time()) // 30 + 1)
        assert client.post("/api/v1/auth/login", json={"username":"mfa-test","password":"synthetic-long-password","totp_code":next_code}).status_code == 200
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
