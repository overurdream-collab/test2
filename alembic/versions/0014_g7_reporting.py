"""G7 append-only report versions; writes validated against tenant and batch."""
from alembic import op
import sqlalchemy as sa

revision = "0014_g7_reporting"
down_revision = "0013_g6_governance"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("report_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("batch_id", sa.String(36),
                  sa.ForeignKey("claim_batches.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("dataset", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("created_by", sa.String(36),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("batch_id", "version", name="uq_g7_report_batch_version"),
        sa.CheckConstraint("version > 0", name="ck_g7_report_version_positive"))
    op.create_index("ix_g7_reports_org", "report_snapshots", ["organization_id"])
    op.create_index("ix_g7_reports_batch", "report_snapshots", ["batch_id"])
    op.execute("""
    CREATE FUNCTION mcias_g7_report_guard() RETURNS trigger AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'frozen G7 report immutable';
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM claim_batches b JOIN users u ON u.id=NEW.created_by
        WHERE b.id=NEW.batch_id AND b.organization_id=NEW.organization_id
          AND u.organization_id=NEW.organization_id AND u.active
      ) THEN
        RAISE EXCEPTION 'G7 tenant or actor mismatch';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql
    """)
    op.execute("""CREATE TRIGGER trg_g7_report_guard
        BEFORE INSERT OR UPDATE OR DELETE ON report_snapshots
        FOR EACH ROW EXECUTE FUNCTION mcias_g7_report_guard()""")

def downgrade():
    raise RuntimeError("frozen report evidence cannot be dropped; restore backup")
