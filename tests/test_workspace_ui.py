"""G5/G6/G7 unified RTL workspace static and security regression."""
from pathlib import Path
from fastapi.testclient import TestClient
from mcias.app import app

client=TestClient(app)

def test_workspace_served_without_data():
    response=client.get("/ui/workspace")
    assert response.status_code==200
    assert 'lang="ar" dir="rtl"' in response.text
    assert 'id="login"' in response.text
    assert 'id="workspace" hidden' in response.text
    assert response.headers["cache-control"]=="no-store"
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert "unsafe-inline" not in response.headers["content-security-policy"]

def test_workspace_allowlisted_assets():
    for asset in ("workspace.css","workspace.js"):
        response=client.get("/ui/workspace/assets/"+asset)
        assert response.status_code==200
        assert response.headers["cache-control"]=="no-store"
    assert client.get("/ui/workspace/assets/../../secret").status_code==404

def test_workspace_no_external_assets_or_inline_js():
    base=Path(__file__).resolve().parents[1]/"mcias"/"web_g7"
    html=(base/"workspace.html").read_text()
    js=(base/"workspace.js").read_text()
    assert "https://" not in html and "http://" not in html
    assert "<script>" not in html and "localStorage" not in js
    assert "sessionStorage" not in js and "innerHTML" not in js
    assert "data-panel=\"claims\"" in html
    assert "data-panel=\"governance\"" in html
