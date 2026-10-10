"""G5 immutable audit snapshots; no mutation of G4 source claims."""
from datetime import datetime
from sqlalchemy import DateTime,ForeignKey,String,JSON,UniqueConstraint,event
from sqlalchemy.orm import Mapped,mapped_column
from mcias.models import Base,uid,now_utc

class AuditSnapshot(Base):
    __tablename__="audit_snapshots"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id:Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True)
    claim_id:Mapped[str]=mapped_column(ForeignKey("claim_entries.id"),nullable=False,index=True)
    policy_id:Mapped[str]=mapped_column(String(120),nullable=False)
    policy_fingerprint:Mapped[str]=mapped_column(String(64),nullable=False)
    calculation:Mapped[dict]=mapped_column(JSON,nullable=False)
    findings:Mapped[dict]=mapped_column(JSON,nullable=False)
    verification:Mapped[dict]=mapped_column(JSON,nullable=False)
    created_by:Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)
    __table_args__=(UniqueConstraint("claim_id","policy_fingerprint",name="uq_g5_claim_policy_snapshot"),)

@event.listens_for(AuditSnapshot,"before_update")
@event.listens_for(AuditSnapshot,"before_delete")
def immutable_snapshot(*args):
    raise ValueError("audit snapshots are immutable")

# Register institutional policy grant mapping for G5 migrations and service use.
from mcias.models_audit_policy import AuditPolicyGrant  # noqa: F401
