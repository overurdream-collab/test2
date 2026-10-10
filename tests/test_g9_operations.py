"""G9 operator readiness: production docs, deterministic synthetic load and release builder."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mcias.performance_g9 import fake_rows, profile
from mcias.release_g9 import ReleaseBlocked
from scripts.g9_release import build, verify

def test_g9_docs_not_accessible_in_production_app():
    env=dict(os.environ, MCIAS_ENVIRONMENT="production",
             MCIAS_DATABASE_URL="postgresql+psycopg://test:test@127.0.0.1/nodb")
    env.pop("MCIAS_BOOTSTRAP_TOKEN",None)
    result=subprocess.run([sys.executable,"-c",
        "from mcias.app import app; "
        "assert app.docs_url is None; "
        "assert app.redoc_url is None; "
        "assert app.openapi_url is None; "
        "from mcias.config import Settings; "
        "assert Settings().bootstrap_token == ''"],
        env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode==0, result.stderr[:500]

def test_g9_benchmark_only_synthetic_deterministic_and_no_institutional_sla():
    first=profile(count=100,repeats=2)
    second=profile(count=100,repeats=2)
    assert first["result_digest"]==second["result_digest"]
    assert first["claim_count"]==100
    assert first["worst_elapsed_ms"]>=0
    assert first["production_performance_accepted"] is False
    assert first["threshold_status"]=="NO_INSTITUTION_APPROVED_SLA"
    assert first["dataset"] == "synthetic_only_no_patient_data"
    for bad in (0,1,10001):
        with pytest.raises(ValueError):
            fake_rows(bad)
    for bad in (0,11):
        with pytest.raises(ValueError):
            profile(count=10,repeats=bad)

def test_g9_release_candidate_copies_only_known_artifacts(tmp_path):
    source=tmp_path/"repo"
    for name in ("deploy/Dockerfile","deploy/nginx.conf","deploy/compose.g9.yml",
                 "docs/G9_RELEASE.md","docs/G0_G8_ACCEPTANCE_TRACKER.md",
                 "GATE_STATUS.md"):
        f=source/name
        f.parent.mkdir(parents=True,exist_ok=True)
        f.write_text("SYNTHETIC RELEASE FILE: "+name)
    wheels=tmp_path/"wheelhouse"
    wheels.mkdir()
    (wheels/"mcias-0.1.0-py3-none-any.whl").write_bytes(b"synthetic wheel")
    (wheels/"dependency-1.0-py3-none-any.whl").write_bytes(b"synthetic dependency")
    output=tmp_path/"candidate"
    head="c"*40
    result=build(source,output,wheels,head)
    assert result["acceptance"]=="OPEN_NOT_AUTHORIZED_FOR_PRODUCTION"
    assert len(result["artifacts"])==8
    assert verify(output)==result
    assert not (output/".env").exists()
    assert not (output/"deploy/private").exists()
    (output/"wheels/dependency-1.0-py3-none-any.whl").write_bytes(b"tampered")
    with pytest.raises(ReleaseBlocked):
        verify(output)
    with pytest.raises(ReleaseBlocked):
        build(source,output,wheels,head)

def test_g9_deployment_sources_are_hard_fail_and_localhost_only():
    root=Path(__file__).resolve().parents[1]
    compose=(root/"deploy"/"compose.g9.yml").read_text()
    dockerfile=(root/"deploy"/"Dockerfile").read_text()
    nginx=(root/"deploy"/"nginx.conf").read_text()
    dockerignore=(root/".dockerignore").read_text()
    assert "127.0.0.1:8443:443" in compose
    assert "no-new-privileges:true" in compose
    assert "internal: true" in compose
    assert 'user: "1900:1900"' in compose
    assert 'MCIAS_ENVIRONMENT: production' in compose
    assert 'private/runtime.env' in compose
    assert 'private/postgres-owner.env' in compose
    assert 'USER 1900:1900' in dockerfile
    assert '--no-access-log' in dockerfile
    assert 'ssl_protocols TLSv1.2 TLSv1.3' in nginx
    assert 'access_log off' in nginx
    assert 'location = /openapi.json' in nginx
    assert 'Strict-Transport-Security' in nginx
    assert 'deploy/private/' in dockerignore
    assert 'dist/' in dockerignore

def test_g9_malformed_config_returns_control_failures_not_passwords():
    from mcias.preflight_g9 import report
    env={"MCIAS_ENVIRONMENT":"production",
         "MCIAS_DATABASE_URL":"not-a-valid-uri with-secret-token",
         "MCIAS_BOOTSTRAP_TOKEN":"",
         "MCIAS_MFA_ENCRYPTION_KEY":"bad"}
    data=report(env)
    assert data["status"]=="BLOCKED"
    assert "with-secret-token" not in json.dumps(data)
