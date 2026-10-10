"""G3 reference tables.

Revision ID: 0007_reference
Revises: 0006_ingestion
"""
from alembic import op
import sqlalchemy as sa
revision = "0007_reference"
down_revision = "0006_ingestion"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("contract_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("provider_code", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("precedence", sa.Integer(), nullable=False),
        sa.Column("authorization_id", sa.String(36), sa.ForeignKey("written_authorizations.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "provider_code", "version", name="uq_contract_version"),
        sa.CheckConstraint("effective_from < effective_until", name="ck_contract_dates"))
    op.create_index("ix_contract_versions_organization_id", "contract_versions", ["organization_id"])
    op.create_table("provider_tariffs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contract_id", sa.String(36), sa.ForeignKey("contract_versions.id"), nullable=False),
        sa.Column("service_code", sa.String(100), nullable=False),
        sa.Column("amount", sa.Numeric(18,4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.UniqueConstraint("contract_id", "service_code", name="uq_tariff_contract_service"),
        sa.CheckConstraint("amount >= 0", name="ck_tariff_nonnegative"))
    op.create_index("ix_provider_tariffs_contract_id", "provider_tariffs", ["contract_id"])
    op.create_table("beneficiary_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.UniqueConstraint("organization_id", "code", name="uq_category_org_code"))
    op.create_index("ix_beneficiary_categories_organization_id", "beneficiary_categories", ["organization_id"])
    op.create_table("beneficiary_enrollments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("beneficiary_token", sa.String(128), nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("beneficiary_categories.id"), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date(), nullable=False),
        sa.CheckConstraint("effective_from < effective_until", name="ck_enrollment_dates"))
    op.create_index("ix_beneficiary_enrollments_organization_id", "beneficiary_enrollments", ["organization_id"])

def downgrade():
    raise RuntimeError("G3 reference history downgrade forbidden; restore verified backup.")
