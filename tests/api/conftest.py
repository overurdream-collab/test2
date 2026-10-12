"""Isolated synthetic identities; real authentication/authorization dependencies.

Tokens are preissued database sessions for most API cases. The authentication
tests also exercise the actual password + MFA login endpoint.
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
import os
from types import SimpleNamespace
from uuid import uuid4
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from mcias.app import app, get_db
from mcias.models import Base, Group, MFAFactor, Organization, Permission, Role, SessionToken, User, UserRole
from mcias.security import hash_password
from mcias.services.rbac_seed import seed_organization
from mcias.services.rbac_service import add_user_to_group

PASSWORD = "SYN-Api-Test-Password-2026"
MFA_SECRET = b"SYN-test-mfa-secret-only-2026"
MFA_KEY = bytes(range(32))

@pytest.fixture(scope="session")
def synthetic_password_hash():
    return hash_password(PASSWORD)

@pytest.fixture
def api_factory(monkeypatch, synthetic_password_hash):
    contexts = []
    previous_overrides = dict(app.dependency_overrides)
    monkeypatch.setenv("MCIAS_MFA_ENCRYPTION_KEY", MFA_KEY.hex())

    def make(seed=True, url=None):
        if url:
            from alembic import command
            from alembic.config import Config
            cfg = Config("alembic.ini")
            cfg.set_main_option("sqlalchemy.url", url)
            # The repository's Alembic env selects its URL from this variable.
            with monkeypatch.context() as migration_env:
                migration_env.setenv("MCIAS_TEST_DATABASE_URL", url)
                command.upgrade(cfg, "head")
            engine = create_engine(url)
        else:
            engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
            @event.listens_for(engine, "connect")
            def foreign_keys(connection, record):
                # Explicit BEGIN gives SQLite real outer transactions before
                # service savepoints, matching PostgreSQL rollback semantics.
                connection.isolation_level = None
                connection.execute("PRAGMA foreign_keys=ON")
            @event.listens_for(engine, "begin")
            def begin(connection):
                connection.exec_driver_sql("BEGIN")
            Base.metadata.create_all(engine)
        ctx = SimpleNamespace(engine=engine, headers={}, ids={}, groups={}, permissions={},
                              password=PASSWORD, mfa_secret=MFA_SECRET)
        with Session(engine) as db:
            org = Organization(name="SYN-API-جهة اختبار")
            other = Organization(name="SYN-API-جهة أخرى")
            db.add_all([org, other]); db.flush()
            ctx.organization_id, ctx.other_organization_id = org.id, other.id
            for name in ("root", "admin", "viewer", "none", "other", "limited", "future", "flag_only", "no_mfa"):
                user = User(organization_id=other.id if name == "other" else org.id,
                    username=f"SYN-{name}-{uuid4().hex}", password_hash=synthetic_password_hash,
                    effective_from=date.today() + timedelta(days=1) if name == "future" else date.today(),
                    is_super_admin=name == "flag_only")
                db.add(user); db.flush()
                ctx.ids[name] = user.id
                if name == "root":
                    ctx.root_username = user.username
                token = f"SYN-token-{uuid4().hex}"
                db.add(SessionToken(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)))
                ctx.headers[name] = {"Authorization": f"Bearer {token}"}
            role = db.scalar(select(Role).where(Role.code == "super_admin"))
            if role is None:
                role = Role(code="super_admin"); db.add(role); db.flush()
            db.add_all([UserRole(user_id=ctx.ids[name], role_id=role.id) for name in ("root", "no_mfa")])
            nonce = os.urandom(12)
            db.add(MFAFactor(user_id=ctx.ids["root"], enabled=True,
                encrypted_secret=nonce + AESGCM(MFA_KEY).encrypt(nonce, MFA_SECRET, ctx.ids["root"].encode())))
            db.flush()
            if seed:
                seed_organization(db, org.id, ctx.ids["root"])
                ctx.groups = {g.code: g.id for g in db.scalars(select(Group).where(Group.organization_id == org.id))}
                ctx.permissions = {p.code: p.id for p in db.scalars(select(Permission))}
                add_user_to_group(db, ctx.ids["admin"], ctx.groups["admin"], ctx.ids["root"])
                add_user_to_group(db, ctx.ids["viewer"], ctx.groups["viewer"], ctx.ids["root"])
            db.commit()

        def database():
            with Session(engine) as db:
                yield db
        app.dependency_overrides[get_db] = database
        ctx.database = database
        ctx.client = TestClient(app)
        ctx.client.__enter__()
        contexts.append(ctx)
        return ctx

    yield make
    for ctx in reversed(contexts):
        ctx.client.__exit__(None, None, None)
        ctx.engine.dispose()
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous_overrides)

@pytest.fixture
def api(api_factory):
    return api_factory()
