"""MFA factors.
Revision ID: 0003_mfa
Revises: 0002_immutable
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_mfa"
down_revision = "0002_immutable"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "mfa_factors",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("encrypted_secret", sa.LargeBinary(), nullable=False),
        sa.Column("last_accepted_counter", sa.Integer(), nullable=False, server_default="-1"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

def downgrade():
    raise RuntimeError("Destructive downgrade of MFA factors is disabled")
