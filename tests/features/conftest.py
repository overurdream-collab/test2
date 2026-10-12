"""Reuse existing identity fixtures unchanged; catalog is the reviewed 0021 fixture."""
import importlib.util
from pathlib import Path
import pytest
from sqlalchemy.orm import Session
from mcias.models_features import FeatureCatalog

_root = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("feature_identity_fixtures", _root / "tests/api/conftest.py")
_fixtures = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixtures)
api_factory = _fixtures.api_factory
synthetic_password_hash = _fixtures.synthetic_password_hash

@pytest.fixture
def features_api(api_factory):
    api = api_factory()
    spec = importlib.util.spec_from_file_location("catalog_fixture", _root / "alembic/versions/0021_organization_features.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with Session(api.engine) as db:
        for row in migration._catalog_rows():
            db.add(FeatureCatalog(**row))
        db.commit()
    return api
