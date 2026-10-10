"""Operational counters; no changes to immutable medical or financial records."""
from datetime import datetime
from sqlalchemy import Index, String, Integer, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base

class RateLimitBucket(Base):
    __tablename__ = "api_rate_limit_buckets"
    scope_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    requests: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (Index("ix_api_bucket_window", "window_start"), CheckConstraint("requests > 0", name="ck_api_bucket_positive"),)
