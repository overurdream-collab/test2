from alembic import op
import sqlalchemy as sa
revision='0012_g5_policy_grants'
down_revision='0011_g5_audit'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('audit_policy_grants',sa.Column('id',sa.String(36),primary_key=True),sa.Column('organization_id',sa.String(36),sa.ForeignKey('organizations.id'),nullable=False),sa.Column('policy_fingerprint',sa.String(64),nullable=False),sa.Column('policy_id',sa.String(120),nullable=False),sa.Column('approver_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('reviewer_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('signature',sa.String(64),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('revoked_at',sa.DateTime(timezone=True)),sa.UniqueConstraint('organization_id','policy_fingerprint',name='uq_g5_policy_grant'),sa.CheckConstraint('approver_id != reviewer_id',name='ck_g5_independent_reviewer'))
    op.create_index('ix_g5_policy_grant_tenant','audit_policy_grants',['organization_id'])

    op.execute("""
    CREATE FUNCTION mcias_g5_grant_guard() RETURNS trigger AS $
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'approval history cannot be deleted';
      END IF;
      IF TG_OP = 'UPDATE' THEN
        IF NEW.id <> OLD.id OR NEW.organization_id <> OLD.organization_id
           OR NEW.policy_fingerprint <> OLD.policy_fingerprint
           OR NEW.policy_id <> OLD.policy_id OR NEW.approver_id <> OLD.approver_id
           OR NEW.reviewer_id <> OLD.reviewer_id OR NEW.signature <> OLD.signature
           OR NEW.created_at <> OLD.created_at OR OLD.revoked_at IS NOT NULL
           OR NEW.revoked_at IS NULL THEN
          RAISE EXCEPTION 'only one-time revocation is allowed';
        END IF;
        RETURN NEW;
      END IF;
      IF NOT EXISTS (SELECT 1 FROM users a JOIN users r ON r.id=NEW.reviewer_id
        WHERE a.id=NEW.approver_id AND a.organization_id=NEW.organization_id
        AND r.organization_id=NEW.organization_id AND a.active AND r.active) THEN
        RAISE EXCEPTION 'signers must be active in the same organization';
      END IF;
      RETURN NEW;
    END; $ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER trg_g5_grant_guard BEFORE INSERT OR UPDATE OR DELETE ON audit_policy_grants FOR EACH ROW EXECUTE FUNCTION mcias_g5_grant_guard()")

def downgrade():
    raise RuntimeError('Approval evidence cannot be dropped by downgrade')
