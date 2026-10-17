"""Append-only insurance input clauses with historical activation/closure events."""
from alembic import op
import sqlalchemy as sa

revision = "0019_input_clauses"
down_revision = "0018_claim_query_indexes"
branch_labels = depends_on = None

def upgrade():
    op.create_table("input_clauses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("section", sa.String(24), nullable=False),
        sa.Column("logical_key", sa.String(100), nullable=False),
        sa.Column("provider_code", sa.String(80), nullable=False),
        sa.Column("insurer_code", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("clause_text", sa.Text(), nullable=False),
        sa.Column("structured_value", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date()),
        sa.Column("source_document_id", sa.String(36), sa.ForeignKey("ingestion_documents.id")),
        sa.Column("source_locator", sa.JSON(), nullable=False),
        sa.Column("replaces_id", sa.String(36), sa.ForeignKey("input_clauses.id")),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "section", "logical_key", "provider_code", "insurer_code",
                            "version", name="uq_input_clause_version"))
    op.create_index("ix_input_clauses_organization_id", "input_clauses", ["organization_id"])
    op.create_index("ix_input_clause_scope", "input_clauses",
        ["organization_id", "section", "provider_code", "insurer_code"])
    op.create_table("input_clause_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("clause_id", sa.String(36), sa.ForeignKey("input_clauses.id"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("effective_on", sa.Date()),
        sa.Column("authorization_id", sa.String(36), sa.ForeignKey("written_authorizations.id"), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("clause_id", "kind", name="uq_input_clause_single_event"))
    if op.get_bind().dialect.name == "postgresql":
        for name in ("input_clauses", "input_clause_events"):
            op.execute(sa.text(f"""
                CREATE FUNCTION reject_{name}_mutation() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN
                RAISE EXCEPTION 'immutable input history'; END $$;
            """))
            op.execute(sa.text(f"""
                CREATE TRIGGER tr_{name}_immutable BEFORE UPDATE OR DELETE
                ON {name} FOR EACH ROW EXECUTE FUNCTION reject_{name}_mutation()
            """))

def downgrade():
    raise RuntimeError("input clause history cannot be destructively rolled back")
