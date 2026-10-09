"""Per-account login throttling persisted in the organization database."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.models import LoginAttempt

WINDOW = timedelta(minutes=15)
MAX_FAILURES = 5

def utc_now():
    return datetime.now(timezone.utc)

def blocked(db: Session, identity_hash: str, now=None) -> bool:
    now = now or utc_now()
    row = db.get(LoginAttempt, identity_hash)
    if row is None:
        return False
    since = row.window_start
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    return since + WINDOW > now and row.failures >= MAX_FAILURES

def record_failure(db: Session, identity_hash: str, now=None):
    now = now or utc_now()
    row = db.get(LoginAttempt, identity_hash)
    if row is None:
        db.add(LoginAttempt(identity_hash=identity_hash, failures=1, window_start=now))
    else:
        since = row.window_start
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        if since + WINDOW <= now:
            row.window_start = now
            row.failures = 1
        else:
            row.failures += 1
    db.commit()

def clear_failures(db: Session, identity_hash: str):
    row = db.get(LoginAttempt, identity_hash)
    if row is not None:
        db.delete(row)
        db.commit()
