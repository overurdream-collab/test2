"""Database-backed atomic API throttling (no seed-provenance migration)."""
from alembic import op
import sqlalchemy as sa
revision = "0017_operational_limits"
down_revision = "0016_g8_signal_review"
branch_labels = depends_on = None

def upgrade():
    op.create_table("api_rate_limit_buckets",
        sa.Column("scope_hash", sa.String(64), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("requests", sa.Integer(), nullable=False),
        sa.CheckConstraint("requests > 0", name="ck_api_bucket_positive"))
    op.create_index("ix_api_bucket_window", "api_rate_limit_buckets", ["window_start"])

def downgrade():
    op.drop_table("api_rate_limit_buckets")
