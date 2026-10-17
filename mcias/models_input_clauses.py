"""Immutable section-specific insurance clauses with append-only activation/closure events."""
from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Integer, JSON, UniqueConstraint, Index, event
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, uid, now_utc

SECTIONS = ("contracts", "providers", "copays", "categories", "exclusions", "approvals", "tariffs")

class InputClause(Base):
    __tablename__ = "input_clauses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(24), nullable=False)
    logical_key: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_code: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    insurer_code: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    clause_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date | None] = mapped_column(Date)
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("ingestion_documents.id"))
    source_locator: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    replaces_id: Mapped[str | None] = mapped_column(ForeignKey("input_clauses.id"))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    __table_args__ = (
        UniqueConstraint("organization_id", "section", "logical_key", "provider_code", "insurer_code", "version", name="uq_input_clause_version"),
        Index("ix_input_clause_scope", "organization_id", "section", "provider_code", "insurer_code"),
    )

class InputClauseEvent(Base):
    __tablename__ = "input_clause_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    clause_id: Mapped[str] = mapped_column(ForeignKey("input_clauses.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    effective_on: Mapped[date | None] = mapped_column(Date)
    authorization_id: Mapped[str] = mapped_column(ForeignKey("written_authorizations.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    __table_args__ = (UniqueConstraint("clause_id", "kind", name="uq_input_clause_single_event"),)

for _model in (InputClause, InputClauseEvent):
    @event.listens_for(_model, "before_update")
    @event.listens_for(_model, "before_delete")
    def _immutable(*_args):
        raise ValueError("input clause history is append-only")
