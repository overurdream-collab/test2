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
