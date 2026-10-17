"""Append-only organization-scoped candidate records; NEVER active financial rules."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, CheckConstraint, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, uid, now_utc

class ContractProposal(Base):
    __tablename__ = "contract_proposals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("ingestion_documents.id"), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("ingestion_jobs.id"), nullable=False)
    candidate_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_id: Mapped[str] = mapped_column(String(160), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(160), nullable=False)
    request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    response_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    __table_args__ = (UniqueConstraint("organization_id","document_id","candidate_hash",name="uq_contract_candidate"),)

class ContractProposalReview(Base):
    __tablename__ = "contract_proposal_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("contract_proposals.id"), nullable=False, unique=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(12), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    __table_args__ = (CheckConstraint("decision IN ('accepted','rejected')", name="ck_contract_review_decision"),)

class ContractProposalPromotion(Base):
    __tablename__ = "contract_proposal_promotions"
    proposal_id: Mapped[str] = mapped_column(ForeignKey("contract_proposals.id"), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    reference_point_id: Mapped[str] = mapped_column(ForeignKey("reference_points.id"), nullable=False, unique=True)
    promoted_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    promoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

@event.listens_for(ContractProposal, "before_update")
@event.listens_for(ContractProposal, "before_delete")
@event.listens_for(ContractProposalReview, "before_update")
@event.listens_for(ContractProposalReview, "before_delete")
@event.listens_for(ContractProposalPromotion, "before_update")
@event.listens_for(ContractProposalPromotion, "before_delete")
def prohibit_history_mutations(*_):
    raise ValueError("contract proposal history is append-only")
