"""Add non-financial contract number and notes for manual G3 drafts; legacy rows remain valid."""
from alembic import op
import sqlalchemy as sa

revision = "0020_manual_contract_metadata"
down_revision = "0019_input_clauses"
branch_labels = depends_on = None

def upgrade():
    op.add_column("contract_versions", sa.Column("contract_number", sa.String(100), nullable=True))
    op.add_column("contract_versions", sa.Column("contract_notes", sa.String(1000), nullable=False, server_default=""))
    op.create_unique_constraint("uq_contract_number_version", "contract_versions",
                                ["organization_id", "contract_number", "version"])

def downgrade():
    raise RuntimeError("contract metadata migration is append-only; no destructive rollback")
