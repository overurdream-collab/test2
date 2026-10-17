"""Immutable temporal input clauses with independent closure events."""
from alembic import op
import sqlalchemy as sa

revision = "0019_reference_points"
down_revision = "0018_claim_query_indexes"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "reference_points",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("section", sa.String(32), nullable=False),
        sa.Column("logical_key", sa.String(120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("clause_text", sa.Text(), nullable=False),
        sa.Column("rule_type", sa.String(24), nullable=False),
        sa.Column("provider_code", sa.String(80)),
        sa.Column("service_code", sa.String(100)),
        sa.Column("amount", sa.Numeric(18, 4)),
        sa.Column("currency", sa.String(3)),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("supersedes_id", sa.String(36), sa.ForeignKey("reference_points.id")),
        sa.Column("source_document_id", sa.String(36), sa.ForeignKey("ingestion_documents.id")),
        sa.Column("source_sha256", sa.String(64)),
        sa.Column("source_locator", sa.JSON()),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "section", "logical_key", "version", name="uq_reference_point_version"),
        sa.CheckConstraint("effective_from < effective_until", name="ck_reference_point_period"),
        sa.CheckConstraint("version >= 1", name="ck_reference_point_version"),
        sa.CheckConstraint("status IN ('draft', 'approved')", name="ck_reference_point_status"),
        sa.CheckConstraint("amount IS NULL OR amount >= 0", name="ck_reference_point_amount"),
    )
    op.create_index("ix_reference_point_lookup", "reference_points",
        ["organization_id", "section", "logical_key", "status", "effective_from"])
    op.create_table(
        "reference_point_closures",
        sa.Column("point_id", sa.String(36), sa.ForeignKey("reference_points.id"), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("effective_until", sa.Date(), nullable=False),
        sa.Column("replaced_by_id", sa.String(36), sa.ForeignKey("reference_points.id"), nullable=False, unique=True),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("approved_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reference_closure_org", "reference_point_closures", ["organization_id"])
    # Database-level immutability is mandatory: blocking ORM updates alone
    # is insufficient when an application uses direct SQL.
    op.execute("""
        CREATE FUNCTION mcias_reference_point_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'reference points cannot be deleted';
            END IF;
            IF (OLD.status <> 'draft' OR NEW.status <> 'approved'
                OR NEW.approved_by IS NULL OR NEW.approved_at IS NULL
                OR (to_jsonb(NEW) - 'status' - 'approved_by' - 'approved_at')
                 IS DISTINCT FROM
                   (to_jsonb(OLD) - 'status' - 'approved_by' - 'approved_at')) THEN
                RAISE EXCEPTION 'reference points are immutable after draft approval';
            END IF;
            RETURN NEW;
        END $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_reference_point_guard
        BEFORE UPDATE OR DELETE ON reference_points
        FOR EACH ROW EXECUTE FUNCTION mcias_reference_point_guard()
    """)
    op.execute("""
        CREATE FUNCTION mcias_reference_closure_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'reference point closures are append-only'; END $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_reference_closure_guard
        BEFORE UPDATE OR DELETE ON reference_point_closures
        FOR EACH ROW EXECUTE FUNCTION mcias_reference_closure_guard()
    """)


def downgrade():
    raise RuntimeError("reference-point history rollback is intentionally blocked")
