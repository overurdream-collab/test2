"""Real group authority, encrypted intake, tenant counts and employee lifecycle."""
from datetime import date, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.models import User, Group, GroupPermission, Organization, AuditLog
from mcias.models_reference import BeneficiaryCategory, BeneficiaryEnrollment
from mcias.services import feature_service as features


@pytest.fixture
def institution(features_api, monkeypatch, tmp_path):
    api = features_api
    monkeypatch.setenv('MCIAS_STORAGE_DIR', str(tmp_path / 'encrypted-sources'))
    monkeypatch.setenv('MCIAS_STORAGE_KEY', 'c3' * 32)
    with Session(api.engine) as db:
        for leaf in features.list_features(db):
            if not leaf.is_container and not leaf.code.startswith('system.'):
                features.grant_feature(db, api.organization_id, leaf.code, api.ids['root'])
        db.commit()
    return api


def record(api, feature, code, **values):
    payload = {'title': 'PRIVATE-' + code, 'effective_from': str(date.today()),
        'values': {'record_code': code, **values}}
    response = api.client.post(f'/api/v1/registry/{feature}/records', json=payload, headers=api.headers['admin'])
    assert response.status_code == 201, response.text
    return response.json()


def test_overview_real_unique_counts_current_versions_and_tenant_privacy(institution):
    a = institution
    with Session(a.engine) as db:
        category = BeneficiaryCategory(organization_id=a.organization_id, code='SYN-category', description='Synthetic')
        foreign = BeneficiaryCategory(organization_id=a.other_organization_id, code='SYN-foreign', description='Foreign')
        db.add_all([category, foreign]); db.flush()
        for token, org, cat in [('SYN-person', a.organization_id, category.id), ('FOREIGN-PERSON', a.other_organization_id, foreign.id)]:
            db.add(BeneficiaryEnrollment(organization_id=org, beneficiary_token=token, category_id=cat,
                effective_from=date.today()-timedelta(days=1), effective_until=date.today()+timedelta(days=1)))
        db.commit()
    record(a, 'beneficiaries.names', 'SYN-name', beneficiary_token='SYN-person', category_code='SYN-category')
    record(a, 'inputs.insurers', 'SYN-contract-1', insurer_code='SYN-insurer', contract_number='SYN-1')
    record(a, 'inputs.insurers', 'SYN-contract-2', insurer_code='SYN-insurer', contract_number='SYN-2')
    record(a, 'providers.hospitals', 'SYN-hospital', provider_code='SYN-provider')
    record(a, 'providers.clinics', 'SYN-clinic', provider_code='SYN-provider')
    response=a.client.get('/api/v1/institution/overview', headers=a.headers['admin'])
    assert response.status_code == 200
    data=response.json(); metrics=data['metrics']
    assert metrics['beneficiaries']['value']==1 and metrics['insurers']['value']==1 and metrics['providers']['value']==1
    assert metrics['users']['value'] > 0 and all(metric['status']=='available' for metric in metrics.values())
    assert data['organization']['id']==a.organization_id and data['financially_active'] is False
    assert 'FOREIGN-PERSON' not in response.text and 'PRIVATE-' not in response.text and 'SYN-person' not in response.text
    assert response.headers['cache-control']=='no-store'


def test_closed_and_future_insurer_contracts_are_not_counted(institution):
    a=institution
    item=record(a,'inputs.insurers','SYN-ended',insurer_code='SYN-ended-company',contract_number='SYN-ended')
    assert a.client.post(f"/api/v1/registry/inputs.insurers/records/{item['id']}/close",json={'reason':'SYN-close','expected_version':1},headers=a.headers['admin']).status_code==200
    response=a.client.post('/api/v1/registry/inputs.insurers/records',json={'title':'SYN-future','effective_from':str(date.today()+timedelta(days=1)),
        'values':{'record_code':'SYN-future','insurer_code':'SYN-future-company','contract_number':'SYN-future'}},headers=a.headers['admin'])
    assert response.status_code==201
    assert a.client.get('/api/v1/institution/overview',headers=a.headers['admin']).json()['metrics']['insurers']['value']==0


def test_metric_feature_revocation_redacts_value_without_fake_zero(institution):
    a=institution
    with Session(a.engine) as db:
        features.revoke_feature(db,a.organization_id,'beneficiaries.names',a.ids['root'],'SYN-revoke');db.commit()
    metric=a.client.get('/api/v1/institution/overview',headers=a.headers['admin']).json()['metrics']['beneficiaries']
    assert metric['status']=='restricted' and metric['value'] is None and metric['sources']==[]


def test_dashboard_authentication_permission_and_entitlement_are_required(institution):
    a=institution
    assert a.client.get('/api/v1/institution/overview').status_code==401
    assert a.client.get('/api/v1/institution/overview',headers=a.headers['none']).status_code==403
    with Session(a.engine) as db:
        features.revoke_feature(db,a.organization_id,'dashboard.summary',a.ids['root'],'SYN-revoke');db.commit()
    assert a.client.get('/api/v1/institution/overview',headers=a.headers['admin']).status_code==403


def test_institution_directory_is_tenant_scoped_bounded_and_protects_self_and_root(institution):
    a=institution
    response=a.client.get('/api/v1/institution/users?organization_id='+a.other_organization_id,headers=a.headers['admin'])
    assert response.status_code==200
    items=response.json()['items']; assert all(u['organization_id']==a.organization_id for u in items)
    assert not any(u['id']==a.ids['other'] for u in items)
    assert not any(u['username'].startswith('SYN-rbac-signer-') for u in items)
    assert all(not u['manageable'] for u in items if u['id'] in (a.ids['admin'],a.ids['root']))
    assert 'password_hash' not in response.text and 'token_hash' not in response.text
    assert a.client.get('/api/v1/institution/users?limit=101',headers=a.headers['admin']).status_code==422
    assert a.client.get('/api/v1/institution/users?q=%25',headers=a.headers['admin']).json()['items']==[]


def test_employee_create_assign_remove_and_close_preserves_history(institution):
    a=institution
    created=a.client.post('/api/v1/users',json={'username':'SYN-new-employee','password':a.password,'full_name_ar':'SYN-test employee'},headers=a.headers['admin'])
    assert created.status_code==201 and 'password' not in created.text
    user=created.json(); group=a.groups['viewer']
    assert a.client.post(f'/api/v1/groups/{group}/members',json={'user_id':user['id']},headers=a.headers['admin']).status_code==201
    directory=a.client.get('/api/v1/institution/users?q=SYN-new-employee',headers=a.headers['admin']).json()
    assert directory['items'][0]['groups'][0]['id']==group
    assert a.client.post(f"/api/v1/groups/{group}/members/{user['id']}/remove",json={'reason':'SYN-role ended'},headers=a.headers['admin']).status_code==200
    assert a.client.post(f"/api/v1/users/{user['id']}/close",json={'reason':'SYN-account ended'},headers=a.headers['admin']).status_code==200
    with Session(a.engine) as db:
        assert db.get(User,user['id']).status=='closed'
        assert db.scalar(select(AuditLog.id).where(AuditLog.action=='user.close',AuditLog.resource_id==user['id']))
    assert a.client.get('/api/v1/institution/users?status=closed',headers=a.headers['admin']).json()['items'][0]['id']==user['id']


def test_assignment_options_are_reviewed_functional_groups_only(institution):
    a=institution
    with Session(a.engine) as db:
        db.add(Group(organization_id=a.organization_id,code='unreviewed',name_ar='SYN-unreviewed',effective_from=date.today(),created_by=a.ids['root']));db.commit()
    response=a.client.get('/api/v1/institution/assignment-groups',headers=a.headers['admin'])
    assert response.status_code==200 and response.json()['items']
    assert all(g['code'] not in ('admin','unreviewed') for g in response.json()['items'])
    assert a.client.get('/api/v1/institution/assignment-groups',headers=a.headers['none']).status_code==403


def test_me_identifies_institution_admin_without_a_fake_legacy_admin_role(institution):
    a=institution
    admin=a.client.get('/api/v1/me/features',headers=a.headers['admin']).json()
    root=a.client.get('/api/v1/me/features',headers=a.headers['root']).json()
    assert admin['institution_admin'] is True and admin['super_admin'] is False
    assert root['super_admin'] is True and root['institution_admin'] is False
    assert 'inputs.insurers' in admin['features'] and 'reference.beneficiaries.read' in admin['permissions']
