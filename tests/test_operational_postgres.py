"""Real PostgreSQL concurrency; no security-control mocks."""
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from mcias.rate_limits import check_limits
from mcias.models_operations import RateLimitBucket

@pytest.mark.skipif(not os.getenv('MCIAS_TEST_DATABASE_URL'),reason='PostgreSQL service required')
def test_concurrent_requests_share_atomic_quota():
    from alembic import command
    from alembic.config import Config
    command.upgrade(Config('alembic.ini'),'head')
    engine=create_engine(os.environ['MCIAS_TEST_DATABASE_URL'])
    ip='SYN-'+uuid4().hex
    now=datetime.now(timezone.utc).replace(second=0,microsecond=0)
    def request(_):
        with Session(engine) as db:
            return check_limits(db,None,ip,now=now,ip_limit=5)
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(request,range(30)))
        assert results.count(None)==5
        assert sum(r is not None for r in results)==25
        with Session(engine) as db:
            bucket=db.scalar(select(RateLimitBucket).where(RateLimitBucket.scope_hash==hashlib.sha256(('ip:'+ip).encode()).hexdigest()))
            assert bucket.requests==30
    finally: engine.dispose()
