"""G6 versioned governance decisions and objection evidence.

Records are append-only; each decision references a frozen G5 snapshot.
"""
from datetime import datetime
from sqlalchemy import DateTime,ForeignKey,String,JSON,Integer,UniqueConstraint,event,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from mcias.models import Base,uid,now_utc

class GovernanceCase(Base):
    __tablename__="governance_cases"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id:Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True)
    claim_id:Mapped[str]=mapped_column(ForeignKey("claim_entries.id"),nullable=False)
    audit_snapshot_id:Mapped[str]=mapped_column(ForeignKey("audit_snapshots.id"),nullable=False)
    opened_by:Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)

class GovernanceEvent(Base):
    __tablename__="governance_events"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    case_id:Mapped[str]=mapped_column(ForeignKey("governance_cases.id"),nullable=False,index=True)
    organization_id:Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True)
    version:Mapped[int]=mapped_column(Integer,nullable=False)
    kind:Mapped[str]=mapped_column(String(32),nullable=False)
    actor_id:Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    snapshot_id:Mapped[str]=mapped_column(ForeignKey("audit_snapshots.id"),nullable=False)
    evidence_document_id:Mapped[str|None]=mapped_column(ForeignKey("ingestion_documents.id"))
    payload:Mapped[dict]=mapped_column(JSON,nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)
    __table_args__=(UniqueConstraint("case_id","version",name="uq_g6_case_version"),
        CheckConstraint("version > 0",name="ck_g6_positive_version"))

@event.listens_for(GovernanceEvent,"before_update")
@event.listens_for(GovernanceEvent,"before_delete")
def immutable_event(*args):
    raise ValueError("governance decisions are append-only")
