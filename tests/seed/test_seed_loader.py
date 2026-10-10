import os
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from mcias.seed.config import SeedConfig
from mcias.seed.loader import load, identifier
from mcias.models import AuditLog
from mcias.models_claims import ClaimEntry

@pytest.mark.skipif(not os.getenv("MCIAS_SEED_TEST_DATABASE_URL"),reason="dedicated seed test database required")
def test_seed_loader_idempotent_and_changed_dataset_denied():
    config=SeedConfig(os.environ["MCIAS_SEED_TEST_DATABASE_URL"],"development")
    first=load(config); second=load(config)
    assert first==second
    engine=create_engine(config.database_url)
    try:
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(ClaimEntry).where(ClaimEntry.organization_id==identifier("organization")))==12
            receipt=db.scalar(select(AuditLog).where(AuditLog.action=="synthetic_seed_loaded"))
            assert "password" not in str(receipt.details)
        with pytest.raises(ValueError): load(SeedConfig(config.database_url,"development",count=13))
    finally: engine.dispose()
