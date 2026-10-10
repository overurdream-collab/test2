"""G8 Arabic Studio HTML, CSP and no-PHI browser boundary tests."""
from pathlib import Path
from fastapi.testclient import TestClient
from mcias.app import app

def test_g8_studio_is_offline_arabic_rtl_no_secrets():
    response=TestClient(app).get("/ui/intelligence")
    assert response.status_code==200
    assert 'lang="ar" dir="rtl"' in response.text
    assert '/ui/intelligence/assets/studio.js' in response.text
    assert '<script>' not in response.text
    assert 'access_token' not in response.text
    assert "no-store" in response.headers["cache-control"]
    csp=response.headers["content-security-policy"]
    for clause in ("script-src 'self'","style-src 'self'",
                   "connect-src 'self'","object-src 'none'",
                   "frame-ancestors 'none'"):
        assert clause in csp
    assert "cdn." not in response.text

def test_g8_web_assets_whitelisted_no_directory_exposure():
    client=TestClient(app)
    for asset,kind in (("studio.css","text/css"),("studio.js","javascript")):
        response=client.get("/ui/intelligence/assets/"+asset)
        assert response.status_code==200
        assert kind in response.headers["content-type"]
        assert response.headers["cache-control"]=="no-store"
        assert "script-src 'self'" in response.headers["content-security-policy"]
    assert client.get("/ui/intelligence/assets/../../models.py").status_code in (404,422)
    assert client.get("/ui/intelligence/assets/index.html").status_code==422

def test_g8_endpoints_prevent_caching_and_enable_no_inlined_js():
    response=TestClient(app).get("/api/v1/intelligence/nonexistent")
    assert response.status_code==404
    assert response.headers["cache-control"]=="no-store"
    assert response.headers["pragma"]=="no-cache"
    assert "default-src 'none'" in response.headers["content-security-policy"]

def test_g7_has_navigation_link_to_g8():
    response=TestClient(app).get("/ui/reports")
    assert response.status_code==200
    assert 'href="/ui/intelligence"' in response.text

def test_g8_js_does_not_expose_unsafe_script_or_token_persistence():
    script=(Path(__file__).resolve().parents[1]/"mcias"/"web_g8"/"studio.js").read_text("utf-8")
    for fragment in ("localStorage","sessionStorage","eval(","innerHTML","document.write("):
        assert fragment not in script
    assert 'cache:"no-store"' in script
    assert 'credentials:"omit"' in script
