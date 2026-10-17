"""Read-only G9 local preflight: missing operational controls must fail closed.

This checks engineering prerequisites, not a signed production gate. Never include
secrets, passwords, database URLs, organization names, or patient data in output.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.serialization import Encoding
from mcias.release_g9 import ReleaseBlocked

EXPECTED_MIGRATION="0020_contract_proposals"
MAX_CERT_DAYS=30
HEX64=re.compile(r"^[0-9a-fA-F]{64}$")

def control(code: str, ok: bool, reason: str) -> dict:
    return {"control":code,"status":"PASS" if ok else "BLOCKED","reason":reason}

def safe_file(path: str | None) -> bool:
    if not path:
        return False
    try:
        file=Path(path)
        stat=file.lstat()
        return file.is_file() and not file.is_symlink() and not bool(stat.st_mode & 0o022)
    except (OSError, TypeError, ValueError):
        return False

def check_runtime_env(env: dict[str,str]) -> list[dict]:
    results=[]
    results.append(control("runtime.environment",
        env.get("MCIAS_ENVIRONMENT")=="production",
        "explicit production setting required; not an activation grant"))
    results.append(control("bootstrap.disabled",
        not env.get("MCIAS_BOOTSTRAP_TOKEN", "").strip(),
        "bootstrap token must be absent in production"))
    try:
        url=make_url(env.get("MCIAS_DATABASE_URL",""))
        configured=(url.get_backend_name()=="postgresql" and
                    url.drivername=="postgresql+psycopg" and
                    bool(url.database and url.username and url.password))
    except Exception:
        configured=False
    results.append(control("database.postgresql",
        configured, "local or isolated PostgreSQL runtime credentials required"))
    mfa=env.get("MCIAS_MFA_ENCRYPTION_KEY","")
    results.append(control("keys.mfa_present",
        bool(HEX64.fullmatch(mfa)) and int(mfa,16)!=0,
        "32-byte nonzero MFA key must be provisioned through protected custody"))
    results.append(control("authorization.registry_permissions",
        safe_file(env.get("MCIAS_AUTHORIZATION_REGISTRY")),
        "trusted-head authorization registry must be read-only and not writable by group/others"))
    results.append(control("release.sha_declared",
        bool(re.fullmatch(r"[a-f0-9]{40}",env.get("MCIAS_RELEASE_COMMIT",""))),
        "deployment must declare exact reviewed commit SHA"))
    return results

def check_certificate(path: str | None, host: str | None,
                      *, now: datetime | None = None) -> dict:
    if not safe_file(path) or not host or len(host)>253:
        return control("tls.certificate",
                       False,"local TLS certificate and hostname required")
    try:
        cert=x509.load_pem_x509_certificate(Path(path).read_bytes())
        present=now or datetime.now(timezone.utc)
        until=cert.not_valid_after_utc
        remaining=(until-present).total_seconds()
        names=cert.extensions.get_extension_for_class(
            x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
        # No wildcard matching: administrators must provision an exact intranet SAN.
        matched=host.lower() in {item.lower() for item in names}
        valid_start=cert.not_valid_before_utc<=present
        ok=remaining>MAX_CERT_DAYS*86400 and matched and valid_start
        return control("tls.certificate",ok,
            "nonexpired locally supplied SAN certificate with >30-day runway required")
    except (ValueError, OSError, x509.ExtensionNotFound, TypeError):
        return control("tls.certificate",False,"certificate parse/SAN validation failed")

def check_postgres_role(database_url: str | None) -> list[dict]:
    """Read-only SQL checks executed using the *actual intended runtime role*."""
    try:
        url=make_url(database_url or "")
        if (url.drivername!="postgresql+psycopg" or not url.username
            or not url.database or not url.password):
            raise ValueError("not a PostgreSQL runtime URL")
        engine=create_engine(url,pool_pre_ping=True,connect_args={"connect_timeout":3})
    except Exception:
        return [control("database.connection",False,"runtime PostgreSQL connection unavailable")]
    try:
        with engine.connect() as connection:
            name=connection.execute(text("SELECT current_user")).scalar_one()
            flags=connection.execute(text(
                "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, "
                "rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
            restricted=not any(flags)
            result=[control("database.role_flags",restricted,
                "runtime account cannot be superuser, create roles/db, replicate or bypass RLS")]
            schema_priv=connection.execute(text(
                "SELECT has_schema_privilege(current_user,'public','CREATE')")).scalar_one()
            result.append(control("database.schema_create",not schema_priv,
                "runtime role must not create objects in public schema"))
            owners=connection.execute(text("""
                SELECT count(*) FROM pg_class c
                JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='public' AND c.relkind IN ('r','p')
                  AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
            """)).scalar_one()
            result.append(control("database.table_ownership",owners==0,
                "runtime role cannot own application tables"))
            audit_mutation=connection.execute(text("""
                SELECT has_table_privilege(current_user,'public.audit_log','UPDATE')
                    OR has_table_privilege(current_user,'public.audit_log','DELETE')
            """)).scalar_one()
            result.append(control("database.audit_mutation",not audit_mutation,
                "application must not update/delete audit records"))
            migration=connection.execute(text(
                "SELECT version_num FROM alembic_version")).scalar_one()
            result.append(control("database.migration_head",
                migration==EXPECTED_MIGRATION,"required schema head must match reviewed G8 schema"))
            return result
    except Exception:
        return [control("database.connection",False,
                        "runtime PostgreSQL permissions/schema check failed")]
    finally:
        engine.dispose()

def report(env: dict[str,str], *, verify_database=False,
           now: datetime | None = None) -> dict:
    controls=check_runtime_env(env)
    controls.append(check_certificate(env.get("MCIAS_TLS_CERT_PATH"),
                                      env.get("MCIAS_TLS_HOST"),now=now))
    if verify_database:
        controls.extend(check_postgres_role(env.get("MCIAS_DATABASE_URL")))
    else:
        controls.append(control("database.runtime_probe",
                False,"runtime PostgreSQL role verification not executed"))
    return {"schema":"mcias-g9-preflight-v1",
            "status":"ENGINEERING_CHECKS_PASS" if all(x["status"]=="PASS" for x in controls)
                     else "BLOCKED",
            "production_accepted":False,
            "human_signoff_required":True,
            "controls":controls}

def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description="MCIAS G9 read-only local preflight")
    parser.add_argument("--check-database",action="store_true",
                        help="query PostgreSQL using runtime credentials (no mutations)")
    args=parser.parse_args(argv)
    outcome=report(dict(os.environ),verify_database=args.check_database)
    print(json.dumps(outcome,ensure_ascii=False,sort_keys=True,indent=2))
    return 0 if outcome["status"]=="ENGINEERING_CHECKS_PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
