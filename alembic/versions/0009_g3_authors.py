"""G3 proposal author identity and duty separation.

Revision ID: 0009_g3_authors
Revises: 0008_g3_guards
"""
from alembic import op
import sqlalchemy as sa
revision="0009_g3_authors"
down_revision="0008_g3_guards"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("contract_versions",sa.Column("created_by",sa.String(36),sa.ForeignKey("users.id"),nullable=True))
    op.create_index("ix_g3_contract_created_by","contract_versions",["created_by"])

def downgrade():
    raise RuntimeError("G3 authorization provenance downgrade forbidden.")
