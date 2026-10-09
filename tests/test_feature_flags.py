from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, User
from mcias.feature_flags import feature_enabled

def test_feature_entitlements_default_deny():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user=User(username="feature-user",password_hash="fixture")
        db.add(user); db.commit()
        assert not feature_enabled(db,user,"claims_export")
        assert not feature_enabled(db,user,"../../override")
        assert not feature_enabled(db,user,"")
        user.active=False
        assert not feature_enabled(db,user,"claims_export")
    engine.dispose()
