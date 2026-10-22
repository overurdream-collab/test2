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

class ReferenceDatasetVersion(Base):
    """A Super Admin attestation over an existing G2 extraction and its scope.

    The dataset's rows remain in ExtractedSourceRecord; no second importer or
    reference-row store is introduced. Completeness is a bounded human assertion.
    """
    __tablename__ = "reference_dataset_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    owner_organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    family: Mapped[str] = mapped_column(String(20), nullable=False)
    dataset_key: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(__import__("sqlalchemy").Integer, nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("ingestion_documents.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(ForeignKey("ingestion_jobs.id"), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date] = mapped_column(Date, nullable=False)
    coverage_from: Mapped[date] = mapped_column(Date, nullable=False)
    coverage_until: Mapped[date] = mapped_column(Date, nullable=False)
    scope: Mapped[dict] = mapped_column(JSON, nullable=False)
    expected_record_count: Mapped[int] = mapped_column(__import__("sqlalchemy").Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_event_id: Mapped[str | None] = mapped_column(ForeignKey("audit_log.id"))
    __table_args__ = (
        UniqueConstraint("organization_id", "family", "dataset_key", "version", name="uq_reference_dataset_version"),
        CheckConstraint("family IN ('beneficiary','contract','tariff','policy','caps','history')", name="ck_reference_dataset_family"),
        CheckConstraint("version > 0 AND expected_record_count > 0", name="ck_reference_dataset_counts"),
        CheckConstraint("effective_from < effective_until AND coverage_from < coverage_until", name="ck_reference_dataset_dates"),
        CheckConstraint("status IN ('draft','approved')", name="ck_reference_dataset_status"),
        CheckConstraint("status <> 'approved' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL AND approval_event_id IS NOT NULL)", name="ck_reference_dataset_approval"),
    )


@event.listens_for(ReferenceDatasetVersion, "before_insert")
def dataset_cannot_start_approved(mapper, connection, target):
    if target.status == "approved":
        raise ValueError("reference dataset must be reviewed after registration")


@event.listens_for(ReferenceDatasetVersion, "before_update")
@event.listens_for(ReferenceDatasetVersion, "before_delete")
def approved_dataset_is_immutable(mapper, connection, target):
    from sqlalchemy import inspect
    state = inspect(target)
    previous = state.attrs.status.history.deleted
    if (previous and previous[0] == "approved") or (not previous and target.status == "approved"):
        raise ValueError("approved reference dataset is immutable")
