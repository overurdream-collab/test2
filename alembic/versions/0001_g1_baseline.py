"""G1 baseline database schema.

Revision ID: 0001_g1
Revises:
"""
from alembic import op
from mcias.models import Base
revision = "0001_g1"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Initial baseline only. Future changes MUST use explicit migration scripts.
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    raise RuntimeError("Destructive downgrade disabled: restore an encrypted backup instead.")
