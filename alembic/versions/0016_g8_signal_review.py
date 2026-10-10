"""G8 immutable human reviews of statistical signals; no fraud findings."""
from alembic import op
import sqlalchemy as sa

revision = "0016_g8_signal_review"
down_revision = "0015_g8_intelligence"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "g8_signal_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("run_id", sa.String(36),
                  sa.ForeignKey("g8_analysis_runs.id"), nullable=False),
        sa.Column("signal_index", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("disposition", sa.String(32), nullable=False),
        sa.Column("reviewer_id", sa.String(36),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id","signal_index","version",
                            name="uq_g8_signal_review_version"),
        sa.CheckConstraint("signal_index >= 0 AND version > 0",
                           name="ck_g8_signal_review_order"),
        sa.CheckConstraint(
            "disposition IN ('false_positive','needs_followup','insufficient_evidence')",
            name="ck_g8_signal_disposition"),
    )
    op.create_index("ix_g8_review_org","g8_signal_reviews",["organization_id"])
    op.create_index("ix_g8_review_run","g8_signal_reviews",["run_id"])
    op.execute("""
    CREATE FUNCTION mcias_g8_review_guard() RETURNS trigger AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'G8 signal review evidence immutable';
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM g8_analysis_runs r JOIN users u ON u.id=NEW.reviewer_id
        WHERE r.id=NEW.run_id AND r.organization_id=NEW.organization_id
          AND r.kind='signals' AND r.created_by<>NEW.reviewer_id
          AND u.organization_id=NEW.organization_id AND u.active
      ) THEN
        RAISE EXCEPTION 'G8 signal review tenant or reviewer mismatch';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql
    """)
    op.execute("""CREATE TRIGGER trg_g8_review_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON g8_signal_reviews
        FOR EACH ROW EXECUTE FUNCTION mcias_g8_review_guard()""")

def downgrade():
    raise RuntimeError("G8 human signal-review evidence is append-only")
