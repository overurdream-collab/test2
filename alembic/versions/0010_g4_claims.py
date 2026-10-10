"""G4 claim import and provenance tables.

Revision ID: 0010_g4_claims
Revises: 0009_g3_authors
"""
from alembic import op
import sqlalchemy as sa
revision="0010_g4_claims"
down_revision="0009_g3_authors"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("claim_batches",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("ingestion_document_id",sa.String(36),sa.ForeignKey("ingestion_documents.id"),nullable=False),
        sa.Column("created_by",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("status",sa.String(32),nullable=False),
        sa.Column("source_sha256",sa.String(64),nullable=False),
        sa.Column("record_count",sa.Integer(),nullable=False),
        sa.Column("imported_count",sa.Integer(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("organization_id","ingestion_document_id",name="uq_batch_document_org"),
        sa.CheckConstraint("record_count >= 0 AND imported_count >= 0 AND imported_count <= record_count",name="ck_batch_counts"))
    op.create_index("ix_claim_batches_organization_id","claim_batches",["organization_id"])
    op.create_table("claim_entries",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("batch_id",sa.String(36),sa.ForeignKey("claim_batches.id"),nullable=False),
        sa.Column("extracted_record_id",sa.String(36),sa.ForeignKey("extracted_source_records.id"),nullable=False),
        sa.Column("source_locator",sa.JSON(),nullable=False),
        sa.Column("source_values",sa.JSON(),nullable=False),
        sa.Column("claim_reference",sa.String(120),nullable=False),
        sa.Column("beneficiary_token",sa.String(128),nullable=False),
        sa.Column("provider_code",sa.String(80),nullable=False),
        sa.Column("service_code",sa.String(100),nullable=False),
        sa.Column("service_date",sa.Date(),nullable=False),
        sa.Column("claimed_amount",sa.Numeric(18,4),nullable=False),
        sa.Column("currency",sa.String(3),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("batch_id","extracted_record_id",name="uq_claim_batch_record"),
        sa.CheckConstraint("claimed_amount >= 0",name="ck_entry_nonnegative"))
    op.create_index("ix_claim_entries_organization_id","claim_entries",["organization_id"])
    op.create_index("ix_claim_entries_batch_id","claim_entries",["batch_id"])
    op.create_table("claim_attachments",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("claim_id",sa.String(36),sa.ForeignKey("claim_entries.id"),nullable=False),
        sa.Column("ingestion_document_id",sa.String(36),sa.ForeignKey("ingestion_documents.id"),nullable=False),
        sa.Column("document_sha256",sa.String(64),nullable=False),
        sa.Column("linked_by",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("claim_id","ingestion_document_id",name="uq_claim_attachment_document"))
    op.create_index("ix_claim_attachments_organization_id","claim_attachments",["organization_id"])
    op.create_index("ix_claim_attachments_claim_id","claim_attachments",["claim_id"])
    op.execute("""
      CREATE FUNCTION mcias_g4_guard_provenance() RETURNS trigger AS $$
      BEGIN
        IF TG_OP IN ('UPDATE','DELETE') THEN
          RAISE EXCEPTION 'G4 claim provenance is immutable';
        END IF;
        IF TG_TABLE_NAME = 'claim_entries' THEN
          IF NOT EXISTS (
            SELECT 1 FROM claim_batches b
            JOIN ingestion_jobs j ON j.document_id=b.ingestion_document_id
            JOIN extracted_source_records r ON r.job_id=j.id
            WHERE b.id=NEW.batch_id AND b.organization_id=NEW.organization_id
              AND r.id=NEW.extracted_record_id
          ) THEN
            RAISE EXCEPTION 'G4 cross-document or cross-tenant claim record';
          END IF;
        ELSIF TG_TABLE_NAME = 'claim_attachments' THEN
          IF NOT EXISTS (
            SELECT 1 FROM claim_entries c JOIN ingestion_documents d
              ON d.id=NEW.ingestion_document_id
            WHERE c.id=NEW.claim_id AND c.organization_id=NEW.organization_id
              AND d.organization_id=NEW.organization_id AND d.sha256=NEW.document_sha256
          ) THEN
            RAISE EXCEPTION 'G4 cross-tenant attachment';
          END IF;
        END IF;
        RETURN NEW;
      END;
      $$ LANGUAGE plpgsql
    """)
    for table in ("claim_entries","claim_attachments"):
        op.execute(f"CREATE TRIGGER trg_g4_{table} BEFORE INSERT OR UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION mcias_g4_guard_provenance()")

def downgrade():
    raise RuntimeError("G4 source-linked claims downgrade forbidden; restore a verified backup.")
