"""Single reviewed group authority, immutable provenance, no automatic grant import.

Revision ID: 0022_rbac_authority
Revises: 0021_organization_features
"""
from alembic import op
import sqlalchemy as sa

revision='0022_rbac_authority'
down_revision='0021_organization_features'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('groups',sa.Column('management_scope',sa.String(30),nullable=False,server_default='functional'))
    # The existing default institution-admin template is classified, not activated.
    op.execute("UPDATE groups SET management_scope='institution_admin' WHERE code='admin' AND status='open'")
    op.create_check_constraint('ck_group_management_scope','groups',"management_scope IN ('functional','institution_admin')")
    op.create_table('rbac_provisionings',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('organization_id',sa.String(36),sa.ForeignKey('organizations.id'),nullable=False),
        sa.Column('applied_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('approved_by',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('approval_reference',sa.String(200),nullable=False),
        sa.Column('manifest',sa.JSON,nullable=False),sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('signature',sa.String(128),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('organization_id','fingerprint',name='uq_rbac_provision_fingerprint'),
        sa.CheckConstraint('applied_by != approved_by',name='ck_rbac_independent_approval'))
    op.create_index('ix_rbac_provisionings_organization_id','rbac_provisionings',['organization_id'])
    op.create_table('rbac_grant_origins',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('organization_id',sa.String(36),sa.ForeignKey('organizations.id'),nullable=False),
        sa.Column('provisioning_id',sa.String(36),sa.ForeignKey('rbac_provisionings.id'),nullable=False),
        sa.Column('group_permission_id',sa.String(36),sa.ForeignKey('group_permissions.id'),unique=True),
        sa.Column('user_group_id',sa.String(36),sa.ForeignKey('user_groups.id'),unique=True),
        sa.Column('source_type',sa.String(40),nullable=False),sa.Column('source_reference',sa.JSON,nullable=False),
        sa.Column('actor_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint('(group_permission_id IS NULL) != (user_group_id IS NULL)',name='ck_rbac_origin_target'))
    op.create_index('ix_rbac_grant_origins_organization_id','rbac_grant_origins',['organization_id'])
    op.create_index('ix_rbac_grant_origins_provisioning_id','rbac_grant_origins',['provisioning_id'])
    for table in ('rbac_provisionings','rbac_grant_origins'):
        op.execute(f'CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION mcias_audit_guard()')
    op.execute("""CREATE FUNCTION mcias_rbac_origin_guard() RETURNS trigger AS $$
    DECLARE target_org varchar(36); approver_org varchar(36);
    BEGIN
      SELECT organization_id INTO approver_org FROM rbac_provisionings WHERE id=NEW.provisioning_id;
      IF NEW.group_permission_id IS NOT NULL THEN
        SELECT gp.organization_id INTO target_org FROM group_permissions gp
        JOIN groups g ON g.id=gp.group_id AND g.organization_id=gp.organization_id
        WHERE gp.id=NEW.group_permission_id;
      ELSE
        SELECT ug.organization_id INTO target_org FROM user_groups ug
        JOIN groups g ON g.id=ug.group_id AND g.organization_id=ug.organization_id
        JOIN users u ON u.id=ug.user_id AND u.organization_id=ug.organization_id
        WHERE ug.id=NEW.user_group_id;
      END IF;
      IF target_org IS NULL OR target_org IS DISTINCT FROM NEW.organization_id
        OR approver_org IS DISTINCT FROM NEW.organization_id
        OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.actor_id AND organization_id=NEW.organization_id) THEN
        RAISE EXCEPTION 'RBAC provenance tenant mismatch';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql""")
    op.execute('CREATE TRIGGER trg_rbac_origin_tenant BEFORE INSERT ON rbac_grant_origins FOR EACH ROW EXECUTE FUNCTION mcias_rbac_origin_guard()')
    # Immutable grant identity, including while open. Closure fields remain writable.
    op.execute("""CREATE FUNCTION mcias_rbac_identity_guard() RETURNS trigger AS $$
    BEGIN
      IF (to_jsonb(NEW) - ARRAY['status','effective_to','closed_by','closed_at','close_reason'])
         IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['status','effective_to','closed_by','closed_at','close_reason']) THEN
        RAISE EXCEPTION 'RBAC grant identity is immutable; create a new grant';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql""")
    for table in ('group_permissions','user_groups'):
        op.execute(f'CREATE TRIGGER trg_{table}_identity BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION mcias_rbac_identity_guard()')

def downgrade():
    # A populated authority history cannot safely be erased or silently roll back.
    if op.get_bind().execute(sa.text('SELECT EXISTS(SELECT 1 FROM rbac_provisionings)')).scalar():
        raise RuntimeError('Reviewed RBAC history exists; downgrade forbidden, restore a reviewed backup')
    for table in ('group_permissions','user_groups'):
        op.execute(f'DROP TRIGGER trg_{table}_identity ON {table}')
    op.execute('DROP FUNCTION mcias_rbac_identity_guard()')
    op.drop_table('rbac_grant_origins');op.drop_table('rbac_provisionings')
    op.execute('DROP FUNCTION mcias_rbac_origin_guard()')
    op.drop_constraint('ck_group_management_scope','groups',type_='check')
    op.drop_column('groups','management_scope')
