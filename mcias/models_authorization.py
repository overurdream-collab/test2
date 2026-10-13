"""Immutable institutional provisioning and grant provenance; no legacy fallback."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, uid, now_utc

class RbacProvisioning(Base):
    __tablename__ = 'rbac_provisionings'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False, index=True)
    applied_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    approved_by: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    approval_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    __table_args__ = (UniqueConstraint('organization_id','fingerprint',name='uq_rbac_provision_fingerprint'),
        CheckConstraint('applied_by != approved_by',name='ck_rbac_independent_approval'))

class RbacGrantOrigin(Base):
    __tablename__ = 'rbac_grant_origins'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), nullable=False, index=True)
    provisioning_id: Mapped[str] = mapped_column(ForeignKey('rbac_provisionings.id'), nullable=False, index=True)
    group_permission_id: Mapped[str | None] = mapped_column(ForeignKey('group_permissions.id'), unique=True)
    user_group_id: Mapped[str | None] = mapped_column(ForeignKey('user_groups.id'), unique=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_reference: Mapped[dict] = mapped_column(JSON, nullable=False)
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    __table_args__ = (CheckConstraint('(group_permission_id IS NULL) != (user_group_id IS NULL)',name='ck_rbac_origin_target'),)

def _immutable(*args):
    raise ValueError('RBAC provisioning history is append-only')

for model in (RbacProvisioning,RbacGrantOrigin):
    event.listen(model,'before_update',_immutable)
    event.listen(model,'before_delete',_immutable)
