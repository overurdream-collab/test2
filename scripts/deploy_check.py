"""Bounded target-host readiness checks; safe JSON, never institutional acceptance.

Only health/public-shell GETs and the existing read-only PostgreSQL role checks.
Does not read .env, send credentials, upload, mutate policies, or install software.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import socket
import ssl
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def result(code, ok, reason):
    return {"control": code, "status": "PASS" if ok else "BLOCKED", "reason": reason}


def valid_origin(value, profile):
    try:
        parsed = urlsplit(value)
        _ = parsed.port
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            return False
        if parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            return False
        if any(ord(c) < 33 or ord(c) == 127 for c in value):
            return False
        return parsed.scheme == "https" or (profile == "test" and parsed.scheme == "http" and
             parsed.hostname in ("localhost", "127.0.0.1", "::1"))
    except ValueError:
        return False


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(origin, path, ca_file=None):
    """No auth headers; TLS verification stays enabled; redirects are rejected."""
    context = ssl.create_default_context(cafile=ca_file)
    opener = build_opener(NoRedirect(), HTTPSHandler(context=context))
    request = Request(origin.rstrip("/") + path, method="GET", headers={"Accept": "application/json"})
    try:
        with opener.open(request, timeout=5) as response:
            return response.status, dict(response.headers), response.read(4097)
    except HTTPError as response:
        # Error bodies may contain private text. They are never emitted or parsed.
        return response.code, dict(response.headers), b""


def health_checks(origin, ca_file, production, fetcher=fetch):
    checks = []
    for path, wanted in [("/health/live", "ok"), ("/health/ready", "ready")]:
        try:
            code, _, body = fetcher(origin, path, ca_file)
            ok = code == 200 and len(body) <= 4096 and json.loads(body).get("status") == wanted
        except Exception:
            ok = False
        checks.append(result("http." + path.rsplit("/", 1)[1], ok, "bounded health GET; TLS/redirect errors fail closed"))
    try:
        code, headers, _ = fetcher(origin, "/login", ca_file)
        lowered = {k.lower(): v for k, v in headers.items()}
        ok = (code == 200 and lowered.get("x-content-type-options") == "nosniff" and
              lowered.get("x-frame-options") == "DENY" and lowered.get("referrer-policy") == "no-referrer" and
              "frame-ancestors 'none'" in lowered.get("content-security-policy", ""))
    except Exception:
        ok = False
    checks.append(result("http.shell_security_headers", ok, "public sign-in shell must retain security headers"))
    if production:
        for path in ("/docs", "/redoc", "/openapi.json"):
            try:
                ok = fetcher(origin, path, ca_file)[0] == 404
            except Exception:
                ok = False
            checks.append(result("http.disabled_" + path.lstrip("/"), ok, "production API documentation must not be exposed"))
    return checks


def scanner_check(env):
    try:
        host = env.get("MCIAS_CLAMAV_HOST", "127.0.0.1")
        port = int(env.get("MCIAS_CLAMAV_PORT", "3310"))
        ok = env.get("MCIAS_MALWARE_SCAN") == "clamav" and host in ("127.0.0.1", "localhost", "::1") and 1 <= port <= 65535
        if ok:
            with socket.create_connection((host, port), timeout=3) as connection:
                connection.settimeout(3)
                connection.sendall(b"zPING\0")
                ok = connection.recv(64).strip(b"\0\r\n ") == b"PONG"
    except (ValueError, OSError):
        ok = False
    return result("scanner.local_ping", ok, "local ClamAV PING only; scanning correctness needs a separate upload test")


def run_checks(env, *, profile, origin, expected_commit, ca_file=None, skip_database=False):
    checks = [result("runtime.python", sys.version_info >= (3, 11), "Python 3.11+; tested baseline uses 3.12"),
              result("target.origin", valid_origin(origin, profile), "HTTPS origin; test profile permits loopback HTTP only")]
    expected_valid = bool(re.fullmatch(r"[a-f0-9]{40}", expected_commit or ""))
    checks.append(result("release.declared_commit", expected_valid and env.get("MCIAS_RELEASE_COMMIT") == expected_commit,
                         "declared full SHA must match independently supplied expected commit"))
    try:
        observed = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL, timeout=3, text=True).strip()
        checks.append(result("release.checkout_commit", expected_valid and observed == expected_commit, "checkout must match expected SHA"))
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, stderr=subprocess.DEVNULL, timeout=3, text=True).strip()
        checks.append(result("release.clean_checkout", not dirty, "tracked engineering files must be unchanged"))
    except (OSError, subprocess.SubprocessError):
        observed = None
        checks.append({"control":"release.checkout_commit", "status":"NOT_RUN", "reason":"archive has no Git identity; independently verify HANDOFF/SHA256SUMS before use"})
    try:
        from mcias.preflight_g9 import check_runtime_env, check_certificate, check_postgres_role, EXPECTED_MIGRATION
        from sqlalchemy.engine import make_url
        checks.append(result("runtime.dependencies", True, "existing MCIAS preflight imports available"))
        if profile == "production":
            checks.extend(check_runtime_env(env))
            checks.append(check_certificate(env.get("MCIAS_TLS_CERT_PATH"), env.get("MCIAS_TLS_HOST")))
            checks.append(result("preview.disabled", env.get("MCIAS_ENABLE_UI_DEMO", "false").lower() != "true", "production profile must not request demo mode"))
            checks.append(scanner_check(env))
        else:
            try:
                url = make_url(env.get("MCIAS_DATABASE_URL", ""))
                isolated = url.drivername == "postgresql+psycopg" and bool(url.database and url.database.endswith("_e2e"))
            except Exception:
                isolated = False
            checks.append(result("test.isolated_database", isolated and env.get("MCIAS_ENVIRONMENT") == "development", "synthetic check requires development and PostgreSQL *_e2e runtime database"))
        for code, variable in [("mfa", "MCIAS_MFA_ENCRYPTION_KEY"), ("storage", "MCIAS_STORAGE_KEY")]:
            value = env.get(variable, "")
            checks.append(result("keys." + code, bool(re.fullmatch(r"[a-fA-F0-9]{64}", value)) and int(value, 16) != 0,
                                 "nonzero 32-byte key configured; custody/rotation not verified"))
        directory = env.get("MCIAS_STORAGE_DIR", "")
        try:
            folder = Path(directory)
            private = bool(directory) and folder.is_dir() and not folder.is_symlink() and not (folder.stat().st_mode & 0o077) and os.access(folder, os.R_OK | os.W_OK)
        except OSError:
            private = False
        checks.append(result("storage.private_access", private, "existing private source directory must be accessible; no probe file is created"))
        if skip_database:
            checks.append(result("database.runtime_probe", False, "database probe explicitly skipped; result remains BLOCKED"))
        else:
            checks.extend(check_postgres_role(env.get("MCIAS_DATABASE_URL")))
    except Exception:
        EXPECTED_MIGRATION = None
        checks.append(result("runtime.dependencies", False, "MCIAS dependencies unavailable; no exception text is disclosed"))
    if checks[1]["status"] == "PASS":
        checks.extend(health_checks(origin, ca_file, profile == "production"))
    checks.append(result("frontend.assets", all((ROOT / "mcias/web_workspace" / name).is_file() for name in
               ["index.html", "app.js", "views.js", "fonts/plex-ar-400.woff2", "icons/audit.svg"]), "local enterprise assets must be present"))
    return {"schema":"mcias-deploy-check-v1", "profile":profile,
            "expected_commit":expected_commit if expected_valid else None,
            "observed_commit": observed if observed and re.fullmatch(r"[a-f0-9]{40}", observed) else None,
            "expected_migration": EXPECTED_MIGRATION,
            "status":"ENGINEERING_CHECKS_PASS" if all(c["status"] == "PASS" for c in checks) else "BLOCKED",
            "production_accepted":False, "human_signoff_required":True, "controls":checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only MCIAS target-host checks; no installation or activation")
    parser.add_argument("--profile", choices=["test", "production"], default="test")
    parser.add_argument("--url", required=True, help="origin only, without credentials, path, query or fragment")
    parser.add_argument("--expected-commit", required=True, help="independently reviewed full 40-character SHA")
    parser.add_argument("--ca-file", help="institutional CA bundle; TLS verification remains enabled")
    parser.add_argument("--skip-database", action="store_true", help="diagnostic only: always leaves outcome BLOCKED")
    args = parser.parse_args(argv)
    outcome = run_checks(dict(os.environ), profile=args.profile, origin=args.url,
                         expected_commit=args.expected_commit, ca_file=args.ca_file, skip_database=args.skip_database)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    return 0 if outcome["status"] == "ENGINEERING_CHECKS_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
