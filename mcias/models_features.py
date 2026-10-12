"""Exact 0021 mappings; feature grants are distinct from RBAC and financial approval."""
from datetime import date, datetime
from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text, func
from sqlalchemy.dialects.postgresql import ExcludeConstraint, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, uid


class FeatureCatalog(Base):
    __tablename__ = "feature_catalog"
    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    parent_code: Mapped[str | None] = mapped_column(String(100), ForeignKey("feature_catalog.code"))
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(200))
    description_ar: Mapped[str | None] = mapped_column(Text)
    description_en: Mapped[str | None] = mapped_column(Text)
    is_container: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        Index("ix_feature_catalog_parent", "parent_code"),
        Index("ix_feature_catalog_category", "category"),
        CheckConstraint("parent_code IS NULL OR parent_code != code", name="ck_feature_catalog_parent"),
    )


class OrganizationFeature(Base):
    __tablename__ = "organization_features"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    feature_code: Mapped[str] = mapped_column(String(100), ForeignKey("feature_catalog.code"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="open")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    granted_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    closed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    close_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        Index("ix_org_features_org", "organization_id"),
        Index("ix_org_features_code", "feature_code"),
        Index("ix_org_features_status", "status"),
        Index("ix_org_features_lookup", "organization_id", "feature_code", "status"),
        CheckConstraint("status IN ('open', 'closed')", name="ck_org_features_status"),
        CheckConstraint("version >= 1", name="ck_org_features_version"),
        CheckConstraint("(status = 'open' AND effective_to IS NULL AND closed_by IS NULL AND closed_at IS NULL AND close_reason IS NULL) OR (status = 'closed' AND effective_to IS NOT NULL AND closed_by IS NOT NULL AND closed_at IS NOT NULL AND close_reason IS NOT NULL AND length(trim(close_reason)) > 0)", name="ck_org_features_lifecycle"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_org_features_dates"),
        UniqueConstraint("organization_id", "feature_code", "version", name="uq_org_features_org_code_version"),
        ExcludeConstraint(("organization_id", "="), ("feature_code", "="),
            (text("daterange(effective_from, COALESCE(effective_to, 'infinity'::date), '[)')"), "&&"),
            where=text("status = 'open'"), using="gist", name="ex_org_features_unique_open").ddl_if(dialect="postgresql"),
    )
