"""G4 immutable source-linked batches, claims and attachments."""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Index, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, JSON, event
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, now_utc, uid

class ClaimBatch(Base):
    __tablename__="claim_batches"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id: Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True)
    ingestion_document_id: Mapped[str]=mapped_column(ForeignKey("ingestion_documents.id"),nullable=False)
    created_by: Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    status: Mapped[str]=mapped_column(String(32),nullable=False,default="staged")
    source_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    record_count: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    imported_count: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)
    __table_args__=(UniqueConstraint("organization_id","ingestion_document_id",name="uq_batch_document_org"),
                    CheckConstraint("record_count >= 0 AND imported_count >= 0 AND imported_count <= record_count",name="ck_batch_counts"))

class ClaimEntry(Base):
    __tablename__="claim_entries"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id: Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True)
    batch_id: Mapped[str]=mapped_column(ForeignKey("claim_batches.id"),nullable=False,index=True)
    extracted_record_id: Mapped[str]=mapped_column(ForeignKey("extracted_source_records.id"),nullable=False)
    source_locator: Mapped[dict]=mapped_column(JSON,nullable=False)
    source_values: Mapped[dict]=mapped_column(JSON,nullable=False)
    claim_reference: Mapped[str]=mapped_column(String(120),nullable=False)
    beneficiary_token: Mapped[str]=mapped_column(String(128),nullable=False)
    provider_code: Mapped[str]=mapped_column(String(80),nullable=False)
    service_code: Mapped[str]=mapped_column(String(100),nullable=False)
    service_date: Mapped[date]=mapped_column(Date,nullable=False)
    claimed_amount: Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False)
    currency: Mapped[str]=mapped_column(String(3),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)
    __table_args__=(Index("ix_claim_org_service_date", "organization_id", "service_date"),
                    Index("ix_claim_org_provider_code", "organization_id", "provider_code"),
                    Index("ix_claim_org_beneficiary_token", "organization_id", "beneficiary_token"),
                    UniqueConstraint("batch_id","extracted_record_id",name="uq_claim_batch_record"),
                    CheckConstraint("claimed_amount >= 0",name="ck_entry_nonnegative"))

class ClaimAttachment(Base):
    __tablename__="claim_attachments"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id: Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True)
    claim_id: Mapped[str]=mapped_column(ForeignKey("claim_entries.id"),nullable=False,index=True)
    ingestion_document_id: Mapped[str]=mapped_column(ForeignKey("ingestion_documents.id"),nullable=False)
    document_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    linked_by: Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)
    __table_args__=(UniqueConstraint("claim_id","ingestion_document_id",name="uq_claim_attachment_document"),)

@event.listens_for(ClaimEntry,"before_update")
@event.listens_for(ClaimEntry,"before_delete")
def immutable_claim_entry(*args):
    raise ValueError("imported claim entry is immutable")

@event.listens_for(ClaimAttachment,"before_update")
@event.listens_for(ClaimAttachment,"before_delete")
def immutable_claim_attachment(*args):
    raise ValueError("claim attachment provenance is immutable")
