"""G3 temporal reference tables; approved versions are append-only."""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, JSON, event
from sqlalchemy.orm import Mapped, mapped_column
from mcias.models import Base, uid, now_utc

class ContractVersion(Base):
    __tablename__ = "contract_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    provider_code: Mapped[str] = mapped_column(String(80), nullable=False)
    contract_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contract_notes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    version: Mapped[int] = mapped_column(__import__("sqlalchemy").Integer, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    precedence: Mapped[int] = mapped_column(__import__("sqlalchemy").Integer, nullable=False, default=0)
    authorization_id: Mapped[str | None] = mapped_column(ForeignKey("written_authorizations.id"))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    __table_args__ = (
        UniqueConstraint("organization_id", "provider_code", "version", name="uq_contract_version"),
        UniqueConstraint("organization_id", "contract_number", "version", name="uq_contract_number_version"),
        CheckConstraint("effective_from < effective_until", name="ck_contract_dates"),
    )

class ProviderTariff(Base):
    __tablename__ = "provider_tariffs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contract_versions.id"), nullable=False, index=True)
    service_code: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    __table_args__ = (UniqueConstraint("contract_id", "service_code", name="uq_tariff_contract_service"),
                       CheckConstraint("amount >= 0", name="ck_tariff_nonnegative"))

class BeneficiaryCategory(Base):
    __tablename__ = "beneficiary_categories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_category_org_code"),)

class BeneficiaryEnrollment(Base):
    __tablename__ = "beneficiary_enrollments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    beneficiary_token: Mapped[str] = mapped_column(String(128), nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("beneficiary_categories.id"), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date] = mapped_column(Date, nullable=False)
    __table_args__ = (CheckConstraint("effective_from < effective_until", name="ck_enrollment_dates"),)

@event.listens_for(ContractVersion, "before_update")
def prevent_approved_contract_mutation(mapper, connection, target):
    from sqlalchemy import inspect
    state = inspect(target)
    if state.attrs.status.history.deleted and state.attrs.status.history.deleted[0] == "approved":
        raise ValueError("approved contract cannot be changed in place")
    if target.status == "approved" and any(state.attrs[name].history.has_changes() for name in
            ("provider_code", "version", "effective_from", "effective_until", "precedence", "organization_id", "created_by")):
        raise ValueError("approved contract content is immutable")

@event.listens_for(ContractVersion, "before_delete")
def prevent_approved_contract_delete(mapper, connection, target):
    if target.status == "approved":
        raise ValueError("approved contract cannot be deleted")

@event.listens_for(ProviderTariff, "before_update")
def prevent_approved_tariff_mutation(mapper, connection, target):
    from sqlalchemy import select
    status = connection.execute(select(ContractVersion.status).where(ContractVersion.id == target.contract_id)).scalar_one_or_none()
    if status == "approved":
        raise ValueError("approved contract tariff is immutable")

@event.listens_for(ProviderTariff, "before_delete")
def prevent_approved_tariff_delete(mapper, connection, target):
    from sqlalchemy import select
    status = connection.execute(select(ContractVersion.status).where(ContractVersion.id == target.contract_id)).scalar_one_or_none()
    if status == "approved":
        raise ValueError("approved contract tariff is immutable")
