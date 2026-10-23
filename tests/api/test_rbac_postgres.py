"""Real PostgreSQL migration, preserved grants, database guards and runtime ACLs."""
import json,os
from datetime import date
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine,select,text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from mcias.models import User,Group,GroupPermission,UserGroup
from mcias.models_authorization import RbacGrantOrigin,RbacProvisioning
from mcias.services import authorization_service as authority,rbac_service as rbac,user_lifecycle as users,rbac_provisioning as plans
from mcias.feature_runtime import setup
from tests.authorization_fixtures import signed_fixture

pytestmark=pytest.mark.skipif(not os.getenv('MCIAS_RBAC_API_DATABASE_URL'),reason='isolated PostgreSQL RBAC database required')

@pytest.mark.parametrize('populated',[False,True])
def test_0022_upgrade_downgrade_upgrade_preserves_original_records(monkeypatch,populated):
    url=make_url(os.environ['MCIAS_RBAC_API_DATABASE_URL']);name='mcias_rbac_upgrade_'+uuid4().hex[:12]
    admin=create_engine(url.set(database='postgres'),isolation_level='AUTOCOMMIT')
    with admin.connect() as conn:conn.execute(text('CREATE DATABASE "'+name+'"'))
    engine=create_engine(url.set(database=name));before={}
    try:
        monkeypatch.setenv('MCIAS_TEST_DATABASE_URL',url.set(database=name).render_as_string(hide_password=False))
        cfg=Config('alembic.ini');command.upgrade(cfg,'0021_organization_features')
        if populated:
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO organizations(id,name,created_at) VALUES ('org','SYN-Existing',now())"))
                conn.execute(text("INSERT INTO users(id,organization_id,username,password_hash,active,created_at) VALUES ('u','org','SYN-existing','synthetic',true,now())"))
                conn.execute(text("INSERT INTO roles(id,code) VALUES ('role','legacy')"))
                conn.execute(text("INSERT INTO permissions(id,code) VALUES ('p','claims.read')"))
                conn.execute(text("INSERT INTO user_roles(user_id,role_id) VALUES ('u','role')"))
                conn.execute(text("INSERT INTO role_permissions(role_id,permission_id) VALUES ('role','p')"))
                conn.execute(text("INSERT INTO groups(id,organization_id,code,name_ar,effective_from,created_by) VALUES ('g','org','staff','SYN-Staff','2024-01-01','u')"))
                conn.execute(text("INSERT INTO group_permissions(id,organization_id,group_id,permission_id,effective_from,granted_by) VALUES ('gp','org','g','p','2024-02-01','u')"))
                conn.execute(text("INSERT INTO user_groups(id,organization_id,user_id,group_id,effective_from,added_by) VALUES ('ug','org','u','g','2024-03-01','u')"))
                conn.execute(text("INSERT INTO audit_log(id,actor_id,action,resource_type,created_at,details) VALUES ('log','u','synthetic_history','test',now(),'{}')"))
                for table in ('users','permissions','role_permissions','user_roles','group_permissions','user_groups','audit_log'):
                    before[table]=conn.scalar(text('SELECT json_agg(t) FROM '+table+' t'))
        for transition in ('upgrade','downgrade','upgrade'):
            getattr(command,transition)(cfg,'0021_organization_features' if transition=='downgrade' else 'head')
            with engine.connect() as conn:
                for table,original in before.items():assert conn.scalar(text('SELECT json_agg(t) FROM '+table+' t'))==original
        with engine.connect() as conn:
            assert conn.scalar(text('SELECT version_num FROM alembic_version'))=='0023_insurer_intake'
            assert conn.scalar(text('SELECT count(*) FROM rbac_provisionings'))==0
            assert conn.scalar(text('SELECT count(*) FROM rbac_grant_origins'))==0
    finally:
        engine.dispose()
        with admin.connect() as conn:conn.execute(text('DROP DATABASE "'+name+'" WITH (FORCE)'))
        admin.dispose()


def test_runtime_can_assign_close_and_transfer_without_full_update_or_delete(api_factory):
    api=api_factory(url=os.environ['MCIAS_RBAC_API_DATABASE_URL']);role='mcias_rbac_probe_'+uuid4().hex[:10]
    with api.engine.begin() as conn:
        conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
        conn.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{role}"'))
        conn.execute(text(f'GRANT INSERT ON users,groups,group_permissions,user_groups,user_permissions,audit_log TO "{role}"'))
    setup(api.engine,role)
    setup(api.engine,role)
    try:
        with api.engine.connect() as conn:
            conn.execute(text(f'SET ROLE "{role}"'));conn.commit()
            with Session(bind=conn) as db:
                assert conn.scalar(text("SELECT has_table_privilege(current_user,'users','UPDATE')")) is False
                assert conn.scalar(text("SELECT has_column_privilege(current_user,'users','password_hash','UPDATE')")) is False
                new=users.create_user(db,api.organization_id,'SYN-runtime-'+uuid4().hex,'synthetic-hash',api.ids['admin']);db.commit()
                membership=rbac.add_user_to_group(db,new.id,api.groups['claims_approver'],api.ids['admin']);db.commit()
                assert authority.check_permission_unified(db,new,'governance.approve')
                users.change_user_group(db,new.id,api.groups['claims_approver'],api.groups['viewer'],api.ids['admin'],'وظيفة جديدة');db.commit()
                assert not authority.check_permission_unified(db,new,'governance.approve')
                assert authority.check_permission_unified(db,new,'users.read')
                users.close_user(db,new.id,api.ids['admin'],'انتهاء العمل');db.commit()
                assert not authority.check_permission_unified(db,new,'users.read')
                assert db.get(UserGroup,membership.id).status=='closed'
                assert db.scalar(select(RbacGrantOrigin.id).where(RbacGrantOrigin.user_group_id==membership.id))
                for sql in ("UPDATE users SET password_hash='forged' WHERE id=:id","DELETE FROM users WHERE id=:id"):
                    with pytest.raises(DBAPIError):
                        with db.begin_nested():db.execute(text(sql),{'id':new.id})
                review=db.scalar(select(RbacProvisioning).where(RbacProvisioning.organization_id==api.organization_id))
                for sql in ("UPDATE rbac_provisionings SET signature='forged' WHERE id=:id","DELETE FROM rbac_provisionings WHERE id=:id"):
                    with pytest.raises(DBAPIError):
                        with db.begin_nested():db.execute(text(sql),{'id':review.id})
            conn.rollback();conn.execute(text('RESET ROLE'));conn.commit()
    finally:
        with api.engine.begin() as conn:
            conn.execute(text(f'DROP OWNED BY "{role}"'));conn.execute(text(f'DROP ROLE "{role}"'))


def test_postgres_owner_cannot_mutate_authoritative_grant_identity_or_cross_tenant_origin(api_factory):
    api=api_factory(url=os.environ['MCIAS_RBAC_API_DATABASE_URL'])
    with Session(api.engine) as db:
        gp=db.scalar(select(GroupPermission).where(GroupPermission.group_id==api.groups['viewer']))
        with pytest.raises(DBAPIError,match='RBAC grant identity'):
            with db.begin_nested():db.execute(text('UPDATE group_permissions SET permission_id=:permission WHERE id=:id'),{'id':gp.id,'permission':api.permissions['claims.approve']})
        ug=UserGroup(organization_id=api.organization_id,user_id=api.ids['none'],group_id=api.groups['viewer'],added_by=api.ids['root'],effective_from=date.today())
        db.add(ug);db.flush()
        review=db.scalar(select(RbacProvisioning).where(RbacProvisioning.organization_id==api.organization_id))
        with pytest.raises(DBAPIError,match='tenant mismatch'):
            with db.begin_nested():
                db.add(RbacGrantOrigin(organization_id=api.other_organization_id,provisioning_id=review.id,user_group_id=ug.id,
                    actor_id=api.ids['other'],source_type='institution_assignment',source_reference={'user_id':api.ids['none'],'group_id':api.groups['viewer']}));db.flush()
        assert db.scalar(select(User.id)) # savepoint leaves session usable
