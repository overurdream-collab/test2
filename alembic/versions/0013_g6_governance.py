"""G6 governance cases, immutable decisions and objection evidence."""
from alembic import op
import sqlalchemy as sa
revision="0013_g6_governance"
down_revision="0012_g5_policy_grants"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("governance_cases",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("audit_snapshot_id",sa.String(36),sa.ForeignKey("audit_snapshots.id"),nullable=False),
        sa.Column("proposed_by",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("state",sa.String(24),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_governance_cases_organization_id","governance_cases",["organization_id"])
    op.create_table("governance_decisions",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("case_id",sa.String(36),sa.ForeignKey("governance_cases.id"),nullable=False),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("version",sa.Integer,nullable=False),
        sa.Column("stage",sa.String(64),nullable=False),
        sa.Column("decision",sa.String(24),nullable=False),
        sa.Column("actor_id",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("evidence",sa.JSON,nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("case_id","version",name="uq_g6_decision_version"))
    op.create_index("ix_governance_decisions_case_id","governance_decisions",["case_id"])
    op.create_table("governance_objections",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("case_id",sa.String(36),sa.ForeignKey("governance_cases.id"),nullable=False),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("document_id",sa.String(36),sa.ForeignKey("ingestion_documents.id"),nullable=False),
        sa.Column("claim_id",sa.String(36),sa.ForeignKey("claim_entries.id"),nullable=False),
        sa.Column("submitted_by",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_governance_objections_case_id","governance_objections",["case_id"])
    op.execute("""
    CREATE FUNCTION mcias_g6_immutable() RETURNS trigger AS $$
    BEGIN
      RAISE EXCEPTION 'G6 decision and objection evidence is immutable';
    END; $$ LANGUAGE plpgsql
    """)
    for table in ("governance_decisions","governance_objections"):
        op.execute("CREATE TRIGGER trg_g6_immutable_"+table+
          " BEFORE UPDATE OR DELETE ON "+table+
          " FOR EACH ROW EXECUTE FUNCTION mcias_g6_immutable()")

def downgrade():
    raise RuntimeError("G6 governance evidence cannot be dropped")
