"""G7 browser and PDF integration; strict CSP, no raw source leak, tenant isolation."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from mcias.app import app, get_db
from mcias import reporting_g7_explorer as explorer
from mcias.report_pdf_ar_g7 import render_arabic_pdf, CANDIDATE_FONTS, font_path
from mcias.reporting_g7 import fingerprint, ReportBlocked

def client():
    return TestClient(app)

def test_g7_browser_is_arabic_rtl_and_has_no_embedded_secrets():
    response = client().get("/ui/reports")
    assert response.status_code == 200
    assert 'lang="ar" dir="rtl"' in response.text
    assert "/ui/reports/assets/dashboard.js" in response.text
    assert "<script>" not in response.text
    assert "access_token" not in response.text
    assert "no-store" in response.headers["cache-control"]
    csp = response.headers["content-security-policy"]
    assert "script-src 'self'" in csp
    assert "connect-src 'self'" in csp
    assert "object-src 'none'" in csp

def test_g7_assets_same_origin_and_whitelisted():
    for path, media in [("dashboard.css","text/css"),("dashboard.js","javascript")]:
        result = client().get("/ui/reports/assets/" + path)
        assert result.status_code == 200
        assert media in result.headers["content-type"]
        assert result.headers["cache-control"] == "no-store"
        assert "script-src 'self'" in result.headers["content-security-policy"]
    assert client().get("/ui/reports/assets/index.html").status_code == 422

def test_g7_api_default_csp_and_no_caching():
    result = client().get("/api/v1/report-explorer/unknown")
    assert result.status_code == 404
    assert "default-src 'none'" in result.headers["content-security-policy"]
    assert "no-store" in result.headers["cache-control"]

def mock_report(org="o1"):
    dataset = {"source_sha256": "a" * 64, "rows": [{
        "claim_id":"claim1", "currency":"YER", "claimed":"100",
        "payable":"50", "deduction":"50", "state":"approved",
        "hold_reason":None,"audit_snapshot_id":"audit1",
        "governance_case_id":"case1", "governance_event_version":2,
        "source_values":{"diagnosis":"not-for-export"},
        "source_locator":{"row":12}, "beneficiary_token":"secret-token",
        "claim_reference":"private-reference"
    }]}
    summary = {"total_claims":1, "by_currency":{"YER":{
        "claimed":"100", "approved_claimed":"100", "held_claimed":"0",
        "payable":"50", "deductions":"50", "approved_count":1, "held_count":0
    }}}
    return SimpleNamespace(id="r1",organization_id=org,batch_id="b1",
                           version=1,fingerprint=fingerprint(dataset,summary),
                           dataset=dataset,summary=summary)

def test_g7_redacted_drilldown_never_returns_source_or_beneficiary(monkeypatch):
    monkeypatch.setattr(explorer,"authorized",
                        lambda *a,**kw:SimpleNamespace(id="user",organization_id="o1"))
    monkeypatch.setattr(explorer,"require_organization",lambda *a,**kw:True)
    db=MagicMock();db.get.return_value=mock_report()
    result=explorer.entries("r1",limit=10,offset=0,db=db)
    assert result["total"]==1
    row=result["items"][0]
    assert row["claimed"]=="100"
    for secret in ["source_values","source_locator","diagnosis","beneficiary_token",
                   "claim_reference","secret-token"]:
        assert secret not in str(result)

def test_g7_explorer_rejects_cross_organization(monkeypatch):
    monkeypatch.setattr(explorer,"authorized",
                        lambda *a,**kw:SimpleNamespace(id="user",organization_id="o1"))
    monkeypatch.setattr(explorer,"require_organization",lambda *a,**kw:True)
    db=MagicMock();db.get.return_value=mock_report(org="o2")
    with pytest.raises(HTTPException) as error:
        explorer.entries("r1",limit=10,offset=0,db=db)
    assert error.value.status_code==404

def test_g7_explorer_rejects_tampered_snapshot(monkeypatch):
    monkeypatch.setattr(explorer,"authorized",
                        lambda *a,**kw:SimpleNamespace(id="user",organization_id="o1"))
    monkeypatch.setattr(explorer,"require_organization",lambda *a,**kw:True)
    report=mock_report()
    report.dataset["rows"][0]["claimed"]="999"
    db=MagicMock();db.get.return_value=report
    with pytest.raises(HTTPException) as error:
        explorer.entries("r1",limit=10,offset=0,db=db)
    assert error.value.status_code==409

def test_g7_local_arabic_font_fails_closed(monkeypatch):
    monkeypatch.setenv("MCIAS_ARABIC_FONT_PATH","/not-a-real-font.ttf")
    with pytest.raises(ReportBlocked,match="font"):
        font_path()

@pytest.mark.skipif(not any(Path(p).is_file() for p in CANDIDATE_FONTS),
                    reason="CI runner lacks a local Arabic TTF")
def test_g7_arabic_pdf_has_local_font_no_raw_source_data():
    report=mock_report()
    output=render_arabic_pdf(report)
    assert output.startswith(b"%PDF")
    assert len(output)>1000
    assert b"not-for-export" not in output
    assert b"secret-token" not in output
