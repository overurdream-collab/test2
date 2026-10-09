"""G2 tenant-scoped ingestion registry.

Revision ID: 0006_ingestion
Revises: 0005_rule_guard
"""
from alembic import op
import sqlalchemy as sa
revision = "0006_ingestion"
down_revision = "0005_rule_guard"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("ingestion_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("source_files.id"), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(250), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("revision_of", sa.String(36), sa.ForeignKey("ingestion_documents.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id","sha256",name="uq_ingestion_org_sha"))
    op.create_index("ix_ingestion_documents_organization_id", "ingestion_documents", ["organization_id"])
    op.create_table("ingestion_jobs",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("document_id",sa.String(36),sa.ForeignKey("ingestion_documents.id"),nullable=False),
        sa.Column("status",sa.String(32),nullable=False),
        sa.Column("manifest",sa.JSON(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("extracted_source_records",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("job_id",sa.String(36),sa.ForeignKey("ingestion_jobs.id"),nullable=False),
        sa.Column("locator",sa.JSON(),nullable=False),
        sa.Column("values",sa.JSON(),nullable=False),
        sa.Column("confidence",sa.Integer(),nullable=False))
    op.create_table("ingestion_quarantine",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("job_id",sa.String(36),sa.ForeignKey("ingestion_jobs.id"),nullable=False),
        sa.Column("reason",sa.String(250),nullable=False),
        sa.Column("locator",sa.JSON(),nullable=False))

def downgrade():
    raise RuntimeError("G2 ingestion provenance downgrade forbidden; restore validated backup.")
