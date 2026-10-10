import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from mcias.models import Base, Organization, User, MFAFactor, AuditLog
from mcias.mfa_recovery import replace_factor

def test_dual_control_recovery_replay_and_self_approval():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            org = Organization(name="recovery-test")
            db.add(org); db.flush()
            people = [User(username="recovery-"+str(i), password_hash="synthetic", organization_id=org.id) for i in range(3)]
            db.add_all(people); db.commit()
            request = {"user_id": people[0].id, "request_id": "synthetic-recovery-0001", "expires_at": (datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat(), "evidence_sha256": hashlib.sha256(b"synthetic-evidence").hexdigest()}
            payload = json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
            keys = {p.id: Ed25519PrivateKey.generate() for p in people}
            pub = {uid: key.public_key().public_bytes_raw() for uid, key in keys.items()}
            signatures = {uid: key.sign(payload).hex() for uid, key in keys.items()}
            with pytest.raises(ValueError, match="two independent"):
                replace_factor(db, request, {people[0].id: signatures[people[0].id], people[1].id: signatures[people[1].id]}, pub, os.urandom(32))
            with pytest.raises(ValueError, match="two independent"):
                replace_factor(db, request, {people[1].id: signatures[people[1].id], people[2].id: "00"*64}, pub, os.urandom(32))
            expired = dict(request, expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
            with pytest.raises(ValueError, match="expired"):
                replace_factor(db, expired, signatures, pub, os.urandom(32))
            key = os.urandom(32)
            secret = replace_factor(db, request, {people[1].id: signatures[people[1].id], people[2].id: signatures[people[2].id]}, pub, key)
            assert len(secret) == 32
            assert db.get(MFAFactor, people[0].id).last_accepted_counter == -1
            assert db.get(MFAFactor, people[0].id).enabled
            assert db.query(AuditLog).filter_by(action="mfa_recovered").count() == 1
            with pytest.raises(ValueError, match="replayed"):
                replace_factor(db, request, signatures, pub, key)
    finally:
        engine.dispose()
