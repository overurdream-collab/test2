"""Current owner decisions, real session guards and isolated synthetic SQLite DBs."""
from datetime import date, timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from tests.api.conftest import api_factory, synthetic_password_hash
from tests.features.conftest import features_api
from mcias.models import AuditLog, User, UserPermission
from mcias.services import feature_service as features, authorization_service as auth


@pytest.fixture
def workspace(features_api, monkeypatch, tmp_path):
    monkeypatch.setenv('MCIAS_RBAC_AUTHORITY','super_admin')
    monkeypatch.setenv('MCIAS_STORAGE_DIR',str(tmp_path/'sources'))
    monkeypatch.setenv('MCIAS_STORAGE_KEY',bytes(range(32)).hex())
    return features_api


def grants(api,codes,user='admin',revision=None,headers=None):
    path=f'/api/v1/admin/access/users/{api.ids[user]}'
    if revision is None:
        response=api.client.get(path,headers=api.headers['root'])
        assert response.status_code==200,response.text
        revision=response.json()['revision']
    return api.client.put(path,json={'codes':codes,'expected_revision':revision,'reason':'SYN external administrative decision'},headers=headers or api.headers['root'])


def enable(api,feature):
    with Session(api.engine) as db:
        features.grant_feature(db,api.organization_id,feature,api.ids['root']);db.commit()


def record(code='SYN-CONTRACT'):
    return {'title':'عقد اصطناعي','effective_from':date.today().isoformat(),
        'values':{'record_code':code,'provider_code':'SYN-HOSPITAL','contract_number':'SYN-2026'}}


def test_default_authority_freezes_old_approved_admin_and_viewer(workspace,monkeypatch):
    api=workspace;monkeypatch.delenv('MCIAS_RBAC_AUTHORITY')
    assert auth.authority_mode()=='super_admin'
    for name in ('admin','viewer','none'):
        assert api.client.get('/api/v1/users',headers=api.headers[name]).status_code==403
        context=api.client.get('/api/v1/me/features',headers=api.headers[name])
        assert context.status_code==200
        assert context.json()['permissions']==[]
    assert api.client.get('/api/v1/users',headers=api.headers['root']).status_code==200


def test_only_super_admin_can_delegate_and_flag_without_role_is_not_enough(workspace):
    api=workspace
    for name in ('admin','viewer','none','flag_only','no_mfa'):
        assert api.client.get('/api/v1/admin/access/catalog',headers=api.headers[name]).status_code==403
    assert api.client.get('/api/v1/admin/access/catalog').status_code==401


def test_invalid_authority_mode_denies_even_technical_bootstrap_permissions(workspace,monkeypatch):
    monkeypatch.setenv('MCIAS_RBAC_AUTHORITY','misspelled-mode')
    with Session(workspace.engine) as db:
        root=db.get(User,workspace.ids['root'])
        assert auth.permission_codes(db,root)==[]
        assert not auth.check_permission_unified(db,root,'users.read')


def test_future_provider_version_preserves_current_dashboard_identity(workspace):
    api=workspace;base='/api/v1/registry/providers.hospitals'
    data={'title':'SYN current hospital','effective_from':date.today().isoformat(),
          'values':{'record_code':'SYN-FUTURE-PROVIDER','provider_code':'SYN-CURRENT'}}
    original=api.client.post(base+'/records',json=data,headers=api.headers['root']).json()
    data.update({'effective_from':(date.today()+timedelta(days=30)).isoformat(),
                 'expected_version':original['version'],'reason':'SYN planned version',
                 'values':{'record_code':'SYN-FUTURE-PROVIDER','provider_code':'SYN-FUTURE'}})
    assert api.client.post(base+f"/records/{original['id']}/replace",json=data,headers=api.headers['root']).status_code==201
    from mcias.services.institution_workspace import _current_intake
    with Session(api.engine) as db:
        root=db.get(User,api.ids['root'])
        assert _current_intake(db,root,'providers.hospitals','provider_code',date.today())=={'SYN-CURRENT'}
        assert _current_intake(db,root,'providers.hospitals','provider_code',date.today()+timedelta(days=30))=={'SYN-FUTURE'}


def test_grant_and_revoke_change_existing_session_immediately(workspace):
    api=workspace
    assert grants(api,['users.read']).status_code==200
    assert api.client.get('/api/v1/users',headers=api.headers['admin']).status_code==200
    assert grants(api,[]).status_code==200
    assert api.client.get('/api/v1/users',headers=api.headers['admin']).status_code==403
    with Session(api.engine) as db:
        assert db.scalar(select(func.count()).select_from(UserPermission))>0
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action=='access.revoke'))==1


def test_stale_editor_and_cross_tenant_grant_are_rejected(workspace):
    api=workspace
    path=f"/api/v1/admin/access/users/{api.ids['admin']}"
    revision=api.client.get(path,headers=api.headers['root']).json()['revision']
    assert grants(api,['users.read'],revision=revision).status_code==200
    assert grants(api,[],revision=revision).status_code==409
    assert grants(api,['users.read'],user='other',revision=revision).status_code==404
    assert api.client.get('/api/v1/users',headers=api.headers['admin']).status_code==200


def test_technical_account_cannot_self_assign_financial_authority(workspace):
    api=workspace
    with Session(api.engine) as db:
        root=db.get(User,api.ids['root'])
        for code in auth.FINANCIAL_APPROVALS:assert not auth.check_permission_unified(db,root,code)
    assert grants(api,['governance.approve'],user='root').status_code==409
    assert grants(api,['groups.permissions.grant']).status_code==409


def test_catalog_has_independent_read_add_edit_for_each_input(workspace):
    response=workspace.client.get('/api/v1/admin/access/catalog',headers=workspace.headers['root'])
    codes={r['code'] for r in response.json()['items']}
    from mcias.schemas.registry import SCHEMAS
    assert {f'registry.{feature}.{operation}' for feature in SCHEMAS for operation in ('read','create','update')}<=codes


def test_read_and_add_do_not_allow_editing_or_other_sections(workspace):
    api=workspace;enable(api,'inputs.contracts')
    assert grants(api,['registry.inputs.contracts.read','registry.inputs.contracts.create']).status_code==200
    base='/api/v1/registry/inputs.contracts'
    result=api.client.post(base+'/records',json=record(),headers=api.headers['admin'])
    assert result.status_code==201,result.text
    row=result.json()
    replacement={**record(),'expected_version':row['version'],'reason':'SYN correction'}
    assert api.client.post(base+f"/records/{row['id']}/replace",json=replacement,headers=api.headers['admin']).status_code==403
    assert api.client.get('/api/v1/registry/inputs.caps/records',headers=api.headers['admin']).status_code==403
    assert api.client.get('/api/v1/me/features',headers=api.headers['admin']).json()['features']==['inputs.contracts']


def test_atomic_replace_preserves_old_source_and_supports_future_version(workspace):
    api=workspace;base='/api/v1/registry/inputs.contracts'
    original=api.client.post(base+'/records',json=record(),headers=api.headers['root']).json()
    replacement={**record(),'title':'عقد اصطناعي محدث','effective_from':(date.today()+timedelta(days=30)).isoformat(),
        'expected_version':original['version'],'reason':'SYN future correction'}
    response=api.client.post(base+f"/records/{original['id']}/replace",json=replacement,headers=api.headers['root'])
    assert response.status_code==201,response.text
    assert response.json()['version']==original['version']+1
    assert response.json()['previous_event_id']==original['event_id']
    history=api.client.get(base+f"/records/{original['id']}/history",headers=api.headers['root']).json()['items']
    assert history[0]['source_sha256']==original['source_sha256']
    assert history[0]['effective_from']==original['effective_from']
    assert history[0]['effective_to'] is None
    assert any(r['status']=='closed' and r['closed_at'] for r in history)
    assert api.client.post(base+f"/records/{original['id']}/replace",json=replacement,headers=api.headers['root']).status_code==409


def test_replace_rolls_back_closure_on_storage_failure(workspace,monkeypatch):
    api=workspace;base='/api/v1/registry/inputs.contracts'
    original=api.client.post(base+'/records',json=record(),headers=api.headers['root']).json()
    from mcias.services import registry_service as service
    actual_store=service.store()
    class BrokenStore:
        def get(self,*args):return actual_store.get(*args)
        def put(self,*args):raise RuntimeError('SYN simulated storage failure')
    monkeypatch.setattr(service,'store',lambda:BrokenStore())
    response=api.client.post(base+f"/records/{original['id']}/replace",json={**record(),'expected_version':original['version'],'reason':'SYN failure'},headers=api.headers['root'])
    assert response.status_code==503
    current=api.client.get(base+f"/records/{original['id']}",headers=api.headers['root']).json()
    assert current['status']=='open' and current['version']==original['version']
    with Session(api.engine) as db:
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.resource_type=='reference_intake'))==1


def test_contract_clause_is_scoped_and_cannot_duplicate_its_number(workspace):
    api=workspace;base='/api/v1/registry/inputs.contracts'
    parent=api.client.post(base+'/records',json=record(),headers=api.headers['root']).json()
    clause={**record('SYN-CLAUSE-1'),'title':'بند اصطناعي','parent_id':parent['id'],'clause_number':'1.1','body':'نص بند تجريبي'}
    first=api.client.post(base+'/records',json=clause,headers=api.headers['root'])
    assert first.status_code==201,first.text
    assert first.json()['parent_id']==parent['id']
    assert api.client.post(base+'/records',json={**clause,'values':{**clause['values'],'record_code':'SYN-OTHER'}},headers=api.headers['root']).status_code==409
    assert api.client.post(base+'/records',json={**clause,'parent_id':str(uuid4())},headers=api.headers['root']).status_code==409


def test_all_synthetic_inputs_are_idempotent_and_do_not_grant_staff_permissions(workspace,monkeypatch):
    from mcias.seed.reference_inputs import seed_reference_inputs
    from mcias.schemas.registry import SCHEMAS
    api=workspace;monkeypatch.setenv('MCIAS_ENVIRONMENT','development');monkeypatch.setenv('MCIAS_LAPTOP_TEST_MODE','synthetic_localhost')
    with Session(api.engine) as db:
        root=db.get(User,api.ids['root'])
        first=seed_reference_inputs(db,root);db.commit()
        second=seed_reference_inputs(db,root);db.commit()
        assert first['records_created']==len(SCHEMAS) and second['records_created']==0
        assert auth.permission_codes(db,db.get(User,api.ids['admin']))==[]
    for feature in SCHEMAS:
        response=api.client.get(f'/api/v1/registry/{feature}/records',headers=api.headers['root'])
        assert response.status_code==200 and response.json()['total']>=1
