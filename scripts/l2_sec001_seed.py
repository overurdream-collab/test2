"""Seed exclusively disposable PostgreSQL L2 fixture; never use a production database."""
import os
from urllib.parse import urlsplit
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from mcias.models import Organization, User

url = os.environ["MCIAS_L2_ISOLATED_DATABASE_URL"]
parts = urlsplit(url)
assert parts.hostname in ("localhost", "127.0.0.1", "::1")
assert parts.path == "/mcias_l2_e2e"
assert os.environ["MCIAS_L2_ALLOW_ISOLATED_TESTS"] == "YES"
engine = create_engine(url)
with engine.connect() as conn:
    assert conn.execute(text("select current_database()")).scalar_one() == "mcias_l2_e2e"
with Session(engine) as db:
    org=Organization(name="L2-SYNTHETIC-TX-001")
    db.add(org); db.flush()
    actor=User(organization_id=org.id,username="l2-synthetic-"+org.id,password_hash="NOT_A_REAL_PASSWORD",active=True)
    db.add(actor);db.commit()
    with open(os.environ["GITHUB_ENV"],"a") as stream:
        stream.write("MCIAS_L2_SYNTHETIC_ACTOR_ID="+actor.id+"\n")
        stream.write("MCIAS_L2_SYNTHETIC_ORGANIZATION_ID="+org.id+"\n")
engine.dispose()
