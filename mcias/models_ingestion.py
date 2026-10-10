"""G2 document registry and immutable extracted source references."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, uid, now_utc

class IngestionDocument(Base):
    __tablename__ = "ingestion_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_files.id"), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(250), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    revision_of: Mapped[str | None] = mapped_column(ForeignKey("ingestion_documents.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    __table_args__ = (UniqueConstraint("organization_id", "sha256", name="uq_ingestion_org_sha"),)

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("ingestion_documents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

class ExtractedSourceRecord(Base):
    __tablename__ = "extracted_source_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey("ingestion_jobs.id"), nullable=False)
    locator: Mapped[dict] = mapped_column(JSON, nullable=False)
    values: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

class QuarantineItem(Base):
    __tablename__ = "ingestion_quarantine"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey("ingestion_jobs.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(250), nullable=False)
    locator: Mapped[dict] = mapped_column(JSON, nullable=False)
