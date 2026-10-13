"""Explicit limiter fixture for authentication tests without an application DB."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from mcias.app import app, get_rate_limit_db
from mcias.models import Base

@pytest.fixture
def limiter_database():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    def dependency():
        with Session(engine) as db: yield db
    app.dependency_overrides[get_rate_limit_db]=dependency
    try: yield
    finally:
        app.dependency_overrides.pop(get_rate_limit_db,None)
        engine.dispose()

@pytest.fixture(autouse=True)
def isolated_rbac_trust_registry(monkeypatch,tmp_path_factory):
    # A separate, empty registry per test; no fixture is activated automatically.
    path=tmp_path_factory.mktemp('synthetic-rbac-trust')/'registry.json'
    import os,shutil
    from pathlib import Path
    previous=Path(os.environ['MCIAS_RBAC_TRUST_REGISTRY']) if os.getenv('MCIAS_RBAC_TRUST_REGISTRY') else None
    if previous and previous.is_file() and not previous.is_symlink():
        shutil.copyfile(previous,path)
        keys=previous.with_suffix('.synthetic-keys.json')
        if keys.is_file() and not keys.is_symlink():
            shutil.copyfile(keys,path.with_suffix('.synthetic-keys.json'))
            path.with_suffix('.synthetic-keys.json').chmod(0o600)
    else:path.write_text('{"trusted_approvers":{}}')
    path.chmod(0o600)
    monkeypatch.setenv('MCIAS_RBAC_TRUST_REGISTRY',str(path))
