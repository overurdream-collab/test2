"""G5 approval registry: server-controlled, revocable institutional policy grants.

An approval record is bound to a trusted signer, independent reviewer and
specific policy digest. Database grants are not a substitute for verifying the
institutional signature before enrollment.
"""
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, CheckConstraint, event
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
    __table_args__=(UniqueConstraint("organization_id","policy_fingerprint",name="uq_g5_policy_grant"),CheckConstraint("approver_id != reviewer_id",name="ck_g5_independent_reviewer"))

@event.listens_for(AuditPolicyGrant,"before_delete")
def prevent_grant_deletion(*args):
    raise ValueError("policy authorization history cannot be deleted")

@event.listens_for(AuditPolicyGrant,"before_update")
def guard_policy_grant_update(mapper, connection, target):
    from sqlalchemy import inspect, select
    state=inspect(target)
    # A loaded NULL appears in history.deleted during the first legitimate
    # revocation. Read the persisted value too, so expiring/unloading the
    # attribute cannot make a second revocation look like the first one.
    previous=connection.execute(select(AuditPolicyGrant.revoked_at).where(
        AuditPolicyGrant.id==target.id)).scalar_one()
    if (target.revoked_at is None or previous is not None
            or not state.attrs.revoked_at.history.has_changes()):
        raise ValueError("only first revocation is allowed")
    for key in ("id","organization_id","policy_fingerprint","policy_id","approver_id","reviewer_id","signature","created_at"):
        if state.attrs[key].history.has_changes():
            raise ValueError("approval identity is immutable")
