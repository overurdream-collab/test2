"""G8 append-only Analysis Studio definitions, state changes and output evidence."""
from datetime import datetime
from sqlalchemy import (DateTime, ForeignKey, String, JSON, Integer,
                        UniqueConstraint, CheckConstraint, event)
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, uid, now_utc

class AnalysisTaskVersion(Base):
    __tablename__ = "g8_analysis_tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                   nullable=False, default=now_utc)
    __table_args__ = (
        UniqueConstraint("organization_id", "code", "version",
                         name="uq_g8_task_code_version"),
        CheckConstraint("version > 0", name="ck_g8_task_positive_version"),
    )

class AnalysisTaskEvent(Base):
    __tablename__ = "g8_analysis_task_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("g8_analysis_tasks.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                   nullable=False, default=now_utc)
    __table_args__ = (
        UniqueConstraint("task_id", "version", name="uq_g8_task_event_version"),
        CheckConstraint("version > 0", name="ck_g8_event_positive_version"),
        CheckConstraint("kind IN ('tested','activated','deactivated')",
                        name="ck_g8_event_kind"),
    )

class AnalysisRun(Base):
    __tablename__ = "g8_analysis_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("g8_analysis_tasks.id"), index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    sources: Mapped[list] = mapped_column(JSON, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                   nullable=False, default=now_utc)
    __table_args__ = (
        CheckConstraint("kind IN ('summary','signals','simulation')",
                        name="ck_g8_run_kind"),
    )

def _immutable(*_args):
    raise ValueError("G8 evidence is append-only")

for klass in (AnalysisTaskVersion, AnalysisTaskEvent, AnalysisRun):
    event.listen(klass, "before_update", _immutable)
    event.listen(klass, "before_delete", _immutable)
