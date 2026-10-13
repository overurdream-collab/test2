"""Default-deny migration, institutional review and administration/finance separation."""
from datetime import date,timedelta
from pathlib import Path
import json,os
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from mcias.models import User,Group,GroupPermission,UserGroup,UserPermission,RolePermission,Role,UserRole,AuditLog
from mcias.models_authorization import RbacProvisioning,RbacGrantOrigin
from mcias.services import authorization_service as authority,rbac_service as rbac,rbac_provisioning as plans
from tests.authorization_fixtures import signed_fixture,approve_fixture


def test_old_and_individual_grants_never_fall_back(api):
    with Session(api.engine) as db:
        role=Role(code='SYN-legacy-unreviewed');db.add(role);db.flush()
        db.add_all([UserRole(user_id=api.ids['none'],role_id=role.id),RolePermission(role_id=role.id,permission_id=api.permissions['claims.read']),
            UserPermission(organization_id=api.organization_id,user_id=api.ids['none'],permission_id=api.permissions['users.read'],granted_by=api.ids['root'],effective_from=date.today())])
        db.commit()
        target=db.get(User,api.ids['none'])
        assert not authority.check_permission_unified(db,target,'claims.read')
        assert not authority.check_permission_unified(db,target,'users.read')
    assert api.client.get('/api/v1/users',headers=api.headers['none']).status_code==403


def test_technical_admin_cannot_approve_finances_even_if_legacy_granted(api):
    with Session(api.engine) as db:
        root=db.get(User,api.ids['root']);role=db.scalar(select(Role).where(Role.code=='super_admin'))
        db.add(RolePermission(role_id=role.id,permission_id=api.permissions['governance.approve']));db.commit()
        for code in authority.FINANCIAL_APPROVALS:assert not authority.check_permission_unified(db,root,code)
        assert authority.check_permission_unified(db,root,'groups.create')
        assert not authority.check_permission_unified(db,root,'groups.members.add')


def test_institution_admin_cannot_configure_groups_or_self_assign(api):
    assert api.client.post('/api/v1/groups',json={'code':'escalation','name_ar':'تصعيد'},headers=api.headers['admin']).status_code==403
    path=f"/api/v1/groups/{api.groups['claims_approver']}/members"
    assert api.client.post(path,json={'user_id':api.ids['admin']},headers=api.headers['admin']).status_code==409
    assert api.client.post(path,json={'user_id':api.ids['none']},headers=api.headers['root']).status_code==403
    assert api.client.post(path,json={'user_id':api.ids['none']},headers=api.headers['admin']).status_code==201
    with Session(api.engine) as db:
        assert authority.check_permission_unified(db,db.get(User,api.ids['none']),'governance.approve')
        assert not authority.check_permission_unified(db,db.get(User,api.ids['admin']),'governance.approve')


def test_reviewed_legacy_migration_preserves_sources_and_is_idempotent(api):
    with Session(api.engine) as db:
        role=Role(code='SYN-reviewed-legacy');db.add(role);db.flush()
        legacy=RolePermission(role_id=role.id,permission_id=api.permissions['claims.read'])
        db.add_all([UserRole(user_id=api.ids['none'],role_id=role.id),legacy]);db.commit()
        plan=plans.preview_migration(db,api.organization_id)
        envelope=signed_fixture(db,api.ids['root'],plan)
        before=db.scalar(select(func.count()).select_from(RolePermission))
    response=api.client.post('/api/v1/admin/rbac/apply',json=envelope,headers=api.headers['root'])
    assert response.status_code==201,response.text
    repeat=api.client.post('/api/v1/admin/rbac/apply',json=envelope,headers=api.headers['root'])
    assert repeat.status_code==201 and repeat.json()['id']==response.json()['id']
    with Session(api.engine) as db:
        assert db.scalar(select(func.count()).select_from(RolePermission))==before
        assert authority.check_permission_unified(db,db.get(User,api.ids['none']),'claims.read')
        assert db.scalar(select(RbacGrantOrigin.id).where(RbacGrantOrigin.source_type=='legacy_role'))
        assert db.scalar(select(AuditLog.id).where(AuditLog.action=='rbac.provision',AuditLog.resource_id==response.json()['id']))


@pytest.mark.parametrize('tamper',['signature','source','actor','untrusted','future','tenant'])
def test_review_rejects_tampering_stale_sources_and_wrong_signers(api,tamper):
    with Session(api.engine) as db:
        plan=plans.preview_configuration(db,api.organization_id,api.groups['reporter'],[api.permissions['claims.read']])
        envelope=signed_fixture(db,api.ids['root'],plan)
        count=db.scalar(select(func.count()).select_from(RbacProvisioning))
        if tamper=='signature':envelope['signature']='0'*128
        if tamper=='source':
            db.add(UserPermission(organization_id=api.organization_id,user_id=api.ids['none'],permission_id=api.permissions['claims.read'],granted_by=api.ids['root'],effective_from=date.today()));db.commit()
        if tamper=='actor':envelope['approved_by']=api.ids['root']
        if tamper=='untrusted':Path(os.environ['MCIAS_RBAC_TRUST_REGISTRY']).write_text('{"trusted_approvers":{}}')
        if tamper=='future':
            signer=db.get(User,envelope['approved_by']);signer.effective_from=date.today()+timedelta(days=1);db.commit()
        if tamper=='tenant':envelope['manifest']['organization_id']=api.other_organization_id
    result=api.client.post('/api/v1/admin/rbac/apply',json=envelope,headers=api.headers['root'])
    assert result.status_code==409,result.text
    with Session(api.engine) as db:assert db.scalar(select(func.count()).select_from(RbacProvisioning))==count


def test_new_config_requires_independent_signature_and_revocation_never_falls_back(api):
    with Session(api.engine) as db:
        role=Role(code='SYN-no-resurrection');db.add(role);db.flush()
        db.add_all([UserRole(user_id=api.ids['viewer'],role_id=role.id),RolePermission(role_id=role.id,permission_id=api.permissions['users.read'])]);db.commit()
        plan=plans.preview_configuration(db,api.organization_id,api.groups['viewer'],[api.permissions['claims.read']])
        envelope=signed_fixture(db,api.ids['root'],plan)
    path=f"/api/v1/groups/{api.groups['viewer']}/permissions"
    assert api.client.post(path,json={'permission_id':api.permissions['claims.read']},headers=api.headers['root']).status_code==409
    result=api.client.post('/api/v1/admin/rbac/apply',json=envelope,headers=api.headers['root'])
    assert result.status_code==201,result.text
    with Session(api.engine) as db:
        viewer=db.get(User,api.ids['viewer'])
        assert authority.check_permission_unified(db,viewer,'claims.read')
        assert not authority.check_permission_unified(db,viewer,'users.read')
        assert db.scalar(select(GroupPermission.id).where(GroupPermission.group_id==api.groups['viewer'],GroupPermission.status=='closed'))


def test_registry_missing_or_invalid_denies_functional_but_preserves_bootstrap(api):
    path=Path(os.environ['MCIAS_RBAC_TRUST_REGISTRY']);path.write_text('[]')
    assert api.client.get('/api/v1/users',headers=api.headers['viewer']).status_code==403
    assert api.client.get('/api/v1/users',headers=api.headers['root']).status_code==200


def test_individual_grant_endpoint_retired_without_new_record(api):
    with Session(api.engine) as db:before=db.scalar(select(func.count()).select_from(UserPermission))
    result=api.client.post(f"/api/v1/users/{api.ids['none']}/permissions",json={'permission_id':api.permissions['claims.read']},headers=api.headers['root'])
    assert result.status_code==409
    with Session(api.engine) as db:assert db.scalar(select(func.count()).select_from(UserPermission))==before


def test_group_membership_revocation_preserves_review_and_grants(api):
    before=api.client.get('/api/v1/admin/rbac/history',headers=api.headers['root']).json()['items']
    path=f"/api/v1/groups/{api.groups['viewer']}/members/{api.ids['viewer']}/remove"
    assert api.client.post(path,json={'reason':'انتهاء المهمة'},headers=api.headers['admin']).status_code==200
    assert api.client.get('/api/v1/users',headers=api.headers['viewer']).status_code==403
    assert api.client.get('/api/v1/admin/rbac/history',headers=api.headers['root']).json()['items']==before


def test_signed_bootstrap_can_assign_first_institution_admin_without_technical_self_grant(api_factory):
    api=api_factory(seed=False)
    assert api.client.post('/api/v1/rbac/seed',headers=api.headers['root']).status_code==200
    with Session(api.engine) as db:
        approve_fixture(db,api.organization_id,api.ids['root']);db.commit()
        group=db.scalar(select(Group).where(Group.organization_id==api.organization_id,Group.code=='admin'))
        from mcias.models import Permission
        ids=list(db.scalars(select(Permission.id).where(Permission.code.in_(['users.read','users.create','groups.members.add','groups.read']))))
        plan=plans.preview_configuration(db,api.organization_id,group.id,ids,[api.ids['admin']])
        envelope=signed_fixture(db,api.ids['root'],plan)
    assert api.client.get('/api/v1/users',headers=api.headers['admin']).status_code==403
    result=api.client.post('/api/v1/admin/rbac/apply',json=envelope,headers=api.headers['root'])
    assert result.status_code==201,result.text
    assert api.client.get('/api/v1/users',headers=api.headers['admin']).status_code==200
    with Session(api.engine) as db:
        assert authority.institution_admin(db,db.get(User,api.ids['admin']))
        assert not authority.check_permission_unified(db,db.get(User,api.ids['admin']),'governance.approve')


def test_technical_contract_approval_is_denied_in_api_and_direct_service(api):
    from mcias.models_reference import ContractVersion
    from mcias.reference import approve_contract,ReferenceConflict
    with Session(api.engine) as db:
        record=ContractVersion(organization_id=api.organization_id,provider_code='SYN-RBAC-CONTRACT',version=1,
            effective_from=date.today(),effective_until=date.today()+timedelta(days=30),status='draft',created_by=api.ids['admin'])
        db.add(record);db.commit();record_id=record.id
        with pytest.raises(ReferenceConflict,match='functional contract-approval'):
            approve_contract(db,record.id,db.get(User,api.ids['root']),date.today(),precedence_approved=True)
        assert db.get(ContractVersion,record.id).status=='draft'
    assert api.client.post(f'/api/v1/reference/contracts/{record_id}/approve',headers=api.headers['root']).status_code==403
    # The approved granular group code reaches the financial safeguards, not a legacy role bypass.
    path=f"/api/v1/groups/{api.groups['reference_manager']}/members"
    assert api.client.post(path,json={'user_id':api.ids['none']},headers=api.headers['admin']).status_code==201
    blocked=api.client.post(f'/api/v1/reference/contracts/{record_id}/approve',headers=api.headers['none'])
    assert blocked.status_code==409 and 'written authorization' in blocked.json()['detail']


def test_repeated_preview_preserves_existing_legacy_group_dates_across_days(api,monkeypatch):
    with Session(api.engine) as db:
        role=Role(code='SYN-dated-migration');db.add(role);db.flush()
        db.add_all([UserRole(user_id=api.ids['none'],role_id=role.id),RolePermission(role_id=role.id,permission_id=api.permissions['claims.read'])])
        db.flush();approve_fixture(db,api.organization_id,api.ids['root']);db.commit()
        today=date.today()
        class NextDay(date):
            @classmethod
            def today(cls):return today+timedelta(days=1)
        monkeypatch.setattr(plans,'date',NextDay)
        preview=plans.preview_migration(db,api.organization_id)
        definition=next(g for g in preview['groups'] if g['code']=='MIG-R-'+role.id[:30])
        assert definition['effective_from']==str(db.get(Group,definition['id']).effective_from)==str(today)
        assert all(p['effective_from']==str(today) for p in definition['permissions'])
        assert all(m['effective_from']==str(today) for m in definition['memberships'])
