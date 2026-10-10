"""G5 approval registry: server-controlled, revocable institutional policy grants.

An approval record is bound to a trusted signer, independent reviewer and
specific policy digest. Database grants are not a substitute for verifying the
institutional signature before enrollment.
"""
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, uid, now_utc

class AuditPolicyGrant(Base):
    __tablename__="audit_policy_grants"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id:Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True)
    policy_fingerprint:Mapped[str]=mapped_column(String(64),nullable=False)
    policy_id:Mapped[str]=mapped_column(String(120),nullable=False)
    approver_id:Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    reviewer_id:Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    signature:Mapped[str]=mapped_column(String(64),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)
    revoked_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    __table_args__=(UniqueConstraint("organization_id","policy_fingerprint",name="uq_g5_policy_grant"),)

@event.listens_for(AuditPolicyGrant,"before_delete")
def prevent_grant_deletion(*args):
    raise ValueError("policy authorization history cannot be deleted")
