"""A1 experimental HTTP gate and authenticated read-only source preview."""
import os
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from mcias.app import app,get_db
from mcias.agents import a1_api
from tests.test_a1_trusted_input import _setup,_claim
from mcias.models import Organization,User

def test_a1_preview_feature_is_off_by_default(tmp_path,monkeypatch):
    monkeypatch.delenv("MCIAS_A1_PREVIEW_ENABLED",raising=False)
    with TestClient(app) as client:
        r=client.get("/api/v1/a1/claims/SYN-unknown/preview")
        assert r.status_code==503

def test_a1_preview_never_enabled_in_production(tmp_path,monkeypatch):
    monkeypatch.setenv("MCIAS_A1_PREVIEW_ENABLED","true")
    monkeypatch.setenv("MCIAS_ENVIRONMENT","production")
    with TestClient(app) as client:
        assert client.get("/api/v1/a1/claims/SYN-unknown/preview").status_code==503

def test_real_g2_g4_preview_http_works_only_for_authorized_user(tmp_path,monkeypatch):
    engine,db,store,org,actor=_setup(tmp_path)
    try:
        claim,_,_=_claim(db,store,org,actor)
        monkeypatch.setenv("MCIAS_ENVIRONMENT","development")
        monkeypatch.setenv("MCIAS_A1_PREVIEW_ENABLED","true")
        monkeypatch.setenv("MCIAS_STORAGE_DIR",str(store.root))
        monkeypatch.setenv("MCIAS_STORAGE_KEY",(b"\x07"*32).hex())
        app.dependency_overrides[get_db]=lambda:db
        with TestClient(app) as client:
            # Real auth subsystem denies missing login, rather than a bypass.
            forbidden=client.get("/api/v1/a1/claims/"+claim.id+"/preview")
            assert forbidden.status_code in (401,403)
            monkeypatch.setattr(a1_api,"resolve_user",lambda db,authorization:(actor,None))
            passed=client.get("/api/v1/a1/claims/"+claim.id+"/preview")
            assert passed.status_code==200,passed.text
            j=passed.json()
            assert j["a1"]["finding_status"]=="INSUFFICIENT_EVIDENCE"
            assert j["financial_decision"]=="NOT_AUTHORIZED"
            assert len(j["source_verifications"])==2
            missing=client.get("/api/v1/a1/claims/SYN-nonexistent/preview")
            assert missing.status_code==404
    finally:
        app.dependency_overrides.clear()
        db.close();engine.dispose()
