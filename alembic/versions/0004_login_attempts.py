"""Login attempt counters.
Revision ID: 0004_login
Revises: 0003_mfa
"""
from alembic import op
import sqlalchemy as sa
revision = "0004_login"
down_revision = "0003_mfa"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "login_attempts",
        sa.Column("identity_hash", sa.String(64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
    )

def downgrade():
    raise RuntimeError("Destructive downgrade disabled")
