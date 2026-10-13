"""G1 baseline database schema.

Revision ID: 0001_g1
Revises:
"""
from alembic import op
import sqlalchemy as sa
revision = "0001_g1"
down_revision = None
branch_labels = None
depends_on = None

def baseline_metadata():
    """Frozen original schema; later ORM fields belong to later revisions."""
    metadata = sa.MetaData()
    sa.Table(
        "organizations", metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "users", metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("username", sa.String(120), unique=True, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "roles", metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(100), unique=True, nullable=False),
    )
    sa.Table(
        "user_roles", metadata,
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id"), primary_key=True),
    )
    sa.Table(
        "source_files", metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sha256", sa.String(64), nullable=False, index=True),
        sa.Column("original_filename", sa.Text, nullable=False),
        sa.Column("storage_key", sa.Text, nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "audit_log", metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(150), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("details", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "claims", metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("source_files.id"), nullable=False),
        sa.Column("original_payload", sa.JSON, nullable=False),
        sa.Column("original_claimed_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("original_claimed_amount >= 0", name="ck_claim_nonnegative"),
    )
    sa.Table(
        "permissions", metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(120), unique=True, nullable=False),
    )
    sa.Table(
        "role_permissions", metadata,
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id"), primary_key=True),
    )
    sa.Table(
        "session_tokens", metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    sa.Table(
        "written_authorizations", metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("source_files.id"), nullable=False),
        sa.Column("approved_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "rule_versions", metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("rule_type", sa.String(60), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("written_authorization_id", sa.String(36), sa.ForeignKey("written_authorizations.id"), nullable=True),
    )
    return metadata


def upgrade():
    baseline_metadata().create_all(bind=op.get_bind())

def downgrade():
    raise RuntimeError("Destructive downgrade disabled: restore an encrypted backup instead.")
