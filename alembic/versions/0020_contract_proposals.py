"""Proposal versions, independent review and promotion are immutable in PostgreSQL."""
from alembic import op
import sqlalchemy as sa

revision="0020_contract_proposals"
down_revision="0019_reference_points"
branch_labels=depends_on=None

def upgrade():
    op.create_table("contract_proposals",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("document_id",sa.String(36),sa.ForeignKey("ingestion_documents.id"),nullable=False),
        sa.Column("job_id",sa.String(36),sa.ForeignKey("ingestion_jobs.id"),nullable=False),
        sa.Column("candidate_hash",sa.String(64),nullable=False),
        sa.Column("candidate",sa.JSON(),nullable=False),
        sa.Column("model_id",sa.String(160),nullable=False),
        sa.Column("model_revision",sa.String(160),nullable=False),
        sa.Column("request_sha256",sa.String(64),nullable=False),
        sa.Column("response_sha256",sa.String(64),nullable=False),
        sa.Column("created_by",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("organization_id","document_id","candidate_hash",name="uq_contract_candidate"))
    op.create_index("ix_contract_proposals_org","contract_proposals",["organization_id"])
    op.create_index("ix_contract_proposals_document","contract_proposals",["document_id"])
    op.create_table("contract_proposal_reviews",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("proposal_id",sa.String(36),sa.ForeignKey("contract_proposals.id"),nullable=False,unique=True),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("decision",sa.String(12),nullable=False),
        sa.Column("reason",sa.Text(),nullable=False),
        sa.Column("reviewer_id",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("reviewed_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("decision IN ('accepted','rejected')",name="ck_contract_review_decision"))
    op.create_table("contract_proposal_promotions",
        sa.Column("proposal_id",sa.String(36),sa.ForeignKey("contract_proposals.id"),primary_key=True),
        sa.Column("organization_id",sa.String(36),sa.ForeignKey("organizations.id"),nullable=False),
        sa.Column("reference_point_id",sa.String(36),sa.ForeignKey("reference_points.id"),nullable=False,unique=True),
        sa.Column("promoted_by",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("promoted_at",sa.DateTime(timezone=True),nullable=False))
    op.execute("""
        CREATE FUNCTION mcias_contract_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        RAISE EXCEPTION 'contract proposal history is immutable';
        END $$;
    """)
    for table in ("contract_proposals","contract_proposal_reviews","contract_proposal_promotions"):
        op.execute(f"""CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE
                      ON {table} FOR EACH ROW EXECUTE FUNCTION mcias_contract_immutable()""")

def downgrade():
    raise RuntimeError("immutable proposal history rollback forbidden")
