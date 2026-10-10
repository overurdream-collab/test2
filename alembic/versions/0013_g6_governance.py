"""G6 append-only governance cases and decisions."""
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
        sa.Column("claim_id",sa.String(36),sa.ForeignKey("claim_entries.id"),nullable=False),
        sa.Column("audit_snapshot_id",sa.String(36),sa.ForeignKey("audit_snapshots.id"),nullable=False),
        sa.Column("opened_by",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_g6_cases_org","governance_cases",["organization_id"])
    op.create_table("governance_events",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("case_id",sa.String(36),sa.ForeignKey("governance_cases.id"),nullable=False),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("version",sa.Integer(),nullable=False),
        sa.Column("kind",sa.String(32),nullable=False),
        sa.Column("actor_id",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("snapshot_id",sa.String(36),sa.ForeignKey("audit_snapshots.id"),nullable=False),
        sa.Column("evidence_document_id",sa.String(36),sa.ForeignKey("ingestion_documents.id")),
        sa.Column("payload",sa.JSON(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("case_id","version",name="uq_g6_case_version"),
        sa.CheckConstraint("version > 0",name="ck_g6_positive_version"))
    op.create_index("ix_g6_events_case","governance_events",["case_id"])
    op.create_index("ix_g6_events_org","governance_events",["organization_id"])
    op.execute("""CREATE FUNCTION mcias_g6_event_immutable() RETURNS trigger AS $body$
    BEGIN RAISE EXCEPTION 'governance event is immutable'; END;
    $body$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER trg_g6_event_immutable BEFORE UPDATE OR DELETE
      ON governance_events FOR EACH ROW EXECUTE FUNCTION mcias_g6_event_immutable()""")

def downgrade():
    raise RuntimeError("governance decision evidence must not be dropped")
