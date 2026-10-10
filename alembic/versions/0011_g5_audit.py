"""G5 immutable financial audit snapshot migration."""
from alembic import op
import sqlalchemy as sa
revision="0011_g5_audit"
down_revision="0010_g4_claims"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("audit_snapshots",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("claim_id",sa.String(36),sa.ForeignKey("claim_entries.id"),nullable=False),
        sa.Column("policy_id",sa.String(120),nullable=False),
        sa.Column("policy_fingerprint",sa.String(64),nullable=False),
        sa.Column("calculation",sa.JSON(),nullable=False),
        sa.Column("findings",sa.JSON(),nullable=False),
        sa.Column("verification",sa.JSON(),nullable=False),
        sa.Column("created_by",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("claim_id","policy_fingerprint",name="uq_g5_claim_policy_snapshot"))
    op.create_index("ix_audit_snapshots_organization_id","audit_snapshots",["organization_id"])
    op.create_index("ix_audit_snapshots_claim_id","audit_snapshots",["claim_id"])
    op.execute("""
    CREATE FUNCTION mcias_g5_snapshot_guard() RETURNS trigger AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'G5 audit snapshot immutable';
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM claim_entries c JOIN users u ON u.id=NEW.created_by
        WHERE c.id=NEW.claim_id AND c.organization_id=NEW.organization_id
          AND u.organization_id=NEW.organization_id AND u.active
      ) THEN
        RAISE EXCEPTION 'G5 tenant or actor mismatch';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql
    """)
    op.execute("""CREATE TRIGGER trg_g5_audit_snapshot
      BEFORE INSERT OR UPDATE OR DELETE ON audit_snapshots
      FOR EACH ROW EXECUTE FUNCTION mcias_g5_snapshot_guard()""")

def downgrade():
    raise RuntimeError("G5 audit evidence cannot be dropped; restore a verified backup")
