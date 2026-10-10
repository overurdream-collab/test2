"""G7 frozen reporting records; source records and audit evidence stay unchanged."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, event, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, now_utc, uid

class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("claim_batches.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    __table_args__ = (
        UniqueConstraint("batch_id", "version", name="uq_g7_report_batch_version"),
        CheckConstraint("version > 0", name="ck_g7_report_version_positive"),
    )

@event.listens_for(ReportSnapshot, "before_update")
@event.listens_for(ReportSnapshot, "before_delete")
def immutable_report(*_args):
    raise ValueError("frozen reports are immutable")
