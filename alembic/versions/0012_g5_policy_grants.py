from alembic import op
import sqlalchemy as sa
revision = '0012_g5_policy_grants'
down_revision = '0011_g5_audit'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('audit_policy_grants', sa.Column('id', sa.String(36), primary_key=True), sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False), sa.Column('policy_fingerprint', sa.String(64), nullable=False), sa.Column('policy_id', sa.String(120), nullable=False), sa.Column('approver_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('reviewer_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False), sa.Column('signature', sa.String(64), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('revoked_at', sa.DateTime(timezone=True)), sa.UniqueConstraint('organization_id', 'policy_fingerprint', name='uq_g5_policy_grant'))

def downgrade():
    op.drop_table('audit_policy_grants')
