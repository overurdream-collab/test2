"""Append-only, organization-scoped reference clause versions and closure events.

These clauses are an advisory/reference register. They do not silently alter the
existing institution-authorized G3 tariffs or G5 financial policy engine.
"""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Integer, JSON, Numeric,
    String, Text, UniqueConstraint, event
)
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, uid, now_utc


class ReferencePoint(Base):
    __tablename__ = "reference_points"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(32), nullable=False)
    logical_key: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    clause_text: Mapped[str] = mapped_column(Text, nullable=False)
    rule_type: Mapped[str] = mapped_column(String(24), nullable=False, default="text")
    provider_code: Mapped[str | None] = mapped_column(String(80))
    service_code: Mapped[str | None] = mapped_column(String(100))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    currency: Mapped[str | None] = mapped_column(String(3))
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("reference_points.id"))
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("ingestion_documents.id"))
    source_sha256: Mapped[str | None] = mapped_column(String(64))
    source_locator: Mapped[dict | None] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("organization_id", "section", "logical_key", "version", name="uq_reference_point_version"),
        CheckConstraint("effective_from < effective_until", name="ck_reference_point_period"),
        CheckConstraint("version >= 1", name="ck_reference_point_version"),
        CheckConstraint("status IN ('draft', 'approved')", name="ck_reference_point_status"),
        CheckConstraint("amount IS NULL OR amount >= 0", name="ck_reference_point_amount"),
    )


class ReferencePointClosure(Base):
    __tablename__ = "reference_point_closures"
    point_id: Mapped[str] = mapped_column(ForeignKey("reference_points.id"), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    effective_until: Mapped[date] = mapped_column(Date, nullable=False)
    replaced_by_id: Mapped[str] = mapped_column(ForeignKey("reference_points.id"), nullable=False, unique=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    approved_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


@event.listens_for(ReferencePoint, "before_update")
def forbid_point_changes(mapper, connection, target):
    from sqlalchemy import inspect
    state = inspect(target)
    changed = {k for k in state.attrs.keys() if state.attrs[k].history.has_changes()}
    # The sole legal in-place transition is a draft becoming approved; all
    # substantive fields and every approved version remain immutable.
    status_history = state.attrs.status.history
    if (changed - {"status", "approved_by", "approved_at"}
        or not status_history.deleted or status_history.deleted[0] != "draft"
        or target.status != "approved"
        or not target.approved_by or not target.approved_at):
        raise ValueError("reference points may only transition draft to approved")


@event.listens_for(ReferencePoint, "before_delete")
@event.listens_for(ReferencePointClosure, "before_delete")
@event.listens_for(ReferencePointClosure, "before_update")
def forbid_reference_history_changes(*_args):
    raise ValueError("reference point history is immutable")
