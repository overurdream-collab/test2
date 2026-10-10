"""G6 versioned governance records; original G4/G5 data remains immutable."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Integer, JSON, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, uid, now_utc

class GovernanceCase(Base):
    __tablename__="governance_cases"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id:Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True)
    audit_snapshot_id:Mapped[str]=mapped_column(ForeignKey("audit_snapshots.id"),nullable=False)
    proposed_by:Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    state:Mapped[str]=mapped_column(String(24),nullable=False,default="pending")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)

class GovernanceDecision(Base):
    __tablename__="governance_decisions"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    case_id:Mapped[str]=mapped_column(ForeignKey("governance_cases.id"),nullable=False,index=True)
    organization_id:Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False)
    version:Mapped[int]=mapped_column(Integer,nullable=False)
    stage:Mapped[str]=mapped_column(String(64),nullable=False)
    decision:Mapped[str]=mapped_column(String(24),nullable=False)
    actor_id:Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    evidence:Mapped[dict]=mapped_column(JSON,nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)
    __table_args__=(UniqueConstraint("case_id","version",name="uq_g6_decision_version"),)

class GovernanceObjection(Base):
    __tablename__="governance_objections"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    case_id:Mapped[str]=mapped_column(ForeignKey("governance_cases.id"),nullable=False,index=True)
    organization_id:Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False)
    document_id:Mapped[str]=mapped_column(ForeignKey("ingestion_documents.id"),nullable=False)
    claim_id:Mapped[str]=mapped_column(ForeignKey("claim_entries.id"),nullable=False)
    submitted_by:Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)

for model in (GovernanceDecision,GovernanceObjection):
    event.listen(model,"before_update",lambda *args: (_ for _ in ()).throw(ValueError("governance evidence is immutable")))
    event.listen(model,"before_delete",lambda *args: (_ for _ in ()).throw(ValueError("governance evidence is immutable")))
