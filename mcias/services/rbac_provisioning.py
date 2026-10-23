"""Reviewed, signed transition to one group authority. Never commits or erases history.

Preview is not authorization. A pinned institutional signer approves the exact
plan; an independent MFA-enabled technical administrator applies it.
"""
from datetime import date
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5
from sqlalchemy import select
from mcias.models import Group, GroupPermission, UserGroup, UserPermission, UserRole, Role, RolePermission, Permission, User, Organization
from mcias.models_authorization import RbacProvisioning, RbacGrantOrigin
from mcias.services import authorization_service as auth


def _id(*parts):
    return str(uuid5(NAMESPACE_URL,'mcias-rbac:'+':'.join(str(x) for x in parts)))


def _dates(record):
    return {'effective_from':str(record.effective_from),'effective_to':str(record.effective_to) if record.effective_to else None}


def _source(db, org_id):
    """Capture original identities and periods, including closed grants for stale checks."""
    sources=[]
    for model, name in ((Group,'group'),(GroupPermission,'group_permission'),(UserGroup,'user_group'),(UserPermission,'user_permission')):
        for row in db.scalars(select(model).where(model.organization_id==org_id).order_by(model.id)):
            entry={'kind':name,'id':row.id,'status':row.status,**_dates(row)}
            for field in ('group_id','user_id','permission_id','code','management_scope'):
                if hasattr(row,field):entry[field]=getattr(row,field)
            sources.append(entry)
    for user, role in db.execute(select(User,Role).join(UserRole,UserRole.user_id==User.id).join(Role,Role.id==UserRole.role_id).where(User.organization_id==org_id).order_by(User.id,Role.id)):
        sources.append({'kind':'legacy_membership','user_id':user.id,'role_id':role.id,'role_code':role.code,'active':auth.live_user(user)})
        for permission in db.scalars(select(Permission).join(RolePermission,RolePermission.permission_id==Permission.id).where(RolePermission.role_id==role.id).order_by(Permission.id)):
            sources.append({'kind':'legacy_permission','role_id':role.id,'permission_id':permission.id,'code':permission.code})
    # Permission codes are part of the digest: a changed code cannot reuse an approval.
    for permission in db.scalars(select(Permission).order_by(Permission.id)):
        sources.append({'kind':'catalog','id':permission.id,'code':permission.code})
    return sources


def preview_migration(db, org_id):
    if db.get(Organization,org_id) is None:raise ValueError('Organization does not exist')
    groups=[];excluded=[]
    def permission_item(row,permission,kind,reference,target_id=None,start=None):
        return {'id':target_id or row.id,'permission_id':permission.id,'code':permission.code,
            **(_dates(row) if start is None else {'effective_from':str(start),'effective_to':None}),
            'source_type':kind,'source_reference':reference}
    for group in db.scalars(select(Group).where(Group.organization_id==org_id,Group.status=='open').order_by(Group.id)):
        # Migrated groups are already represented by their original sources below.
        if group.code.startswith('MIG-'):continue
        definition={'id':group.id,'code':group.code,'name_ar':group.name_ar,'scope':group.management_scope,
            'effective_from':str(group.effective_from),'permissions':[],'memberships':[]}
        for row,permission in db.execute(select(GroupPermission,Permission).join(Permission,Permission.id==GroupPermission.permission_id).where(GroupPermission.group_id==group.id,GroupPermission.organization_id==org_id,GroupPermission.status=='open').order_by(GroupPermission.id)):
            if auth.allowed_in_group(permission.code,group.management_scope):
                definition['permissions'].append(permission_item(row,permission,'existing_group',{'group_permission_id':row.id}))
            else:excluded.append({'source_id':row.id,'code':permission.code,'reason':'technical_or_financial_separation'})
        for row in db.scalars(select(UserGroup).where(UserGroup.group_id==group.id,UserGroup.organization_id==org_id,UserGroup.status=='open').order_by(UserGroup.id)):
            user=db.get(User,row.user_id)
            if user and user.organization_id==org_id:
                definition['memberships'].append({'id':row.id,'user_id':row.user_id,**_dates(row),'source_type':'existing_group','source_reference':{'user_group_id':row.id}})
            else:excluded.append({'source_id':row.id,'reason':'technical_account_not_functional'})
        groups.append(definition)
    today=date.today()
    roles={r.id:r for r in db.scalars(select(Role).join(UserRole).join(User,User.id==UserRole.user_id).where(User.organization_id==org_id).distinct())}
    for role in sorted(roles.values(),key=lambda r:r.id):
        if role.code=='super_admin':
            excluded.append({'source_id':role.id,'reason':'technical_identity_only'});continue
        group_id=_id(org_id,'role',role.id)
        existing_group=db.get(Group,group_id)
        definition={'id':group_id,'code':'MIG-R-'+role.id[:30],'name_ar':'ترحيل فئة: '+role.code,
            'scope':'functional','effective_from':str(existing_group.effective_from if existing_group else today),'permissions':[],'memberships':[]}
        for permission in db.scalars(select(Permission).join(RolePermission,RolePermission.permission_id==Permission.id).where(RolePermission.role_id==role.id).order_by(Permission.id)):
            if not auth.allowed_in_group(permission.code,'functional'):
                excluded.append({'source_id':role.id,'code':permission.code,'reason':'technical_or_admin_permission_requires_separate_review'});continue
            grant_id=_id(org_id,'role_permission',role.id,permission.id)
            existing=db.get(GroupPermission,grant_id)
            if existing and existing.status!='open':continue
            definition['permissions'].append(permission_item(existing,permission,'legacy_role',{'role_id':role.id,'permission_id':permission.id},grant_id,None if existing else today))
        for user in db.scalars(select(User).join(UserRole).where(UserRole.role_id==role.id,User.organization_id==org_id).order_by(User.id)):
            if not auth.live_user(user):continue
            grant_id=_id(org_id,'role_membership',role.id,user.id);existing=db.get(UserGroup,grant_id)
            if existing and existing.status!='open':continue
            definition['memberships'].append({'id':grant_id,'user_id':user.id,**(_dates(existing) if existing else {'effective_from':str(today),'effective_to':None}),'source_type':'legacy_role','source_reference':{'role_id':role.id,'user_id':user.id}})
        if definition['permissions'] and definition['memberships']:groups.append(definition)
    for row,permission in db.execute(select(UserPermission,Permission).join(Permission,Permission.id==UserPermission.permission_id).where(UserPermission.organization_id==org_id,UserPermission.status=='open').order_by(UserPermission.id)):
        user=db.get(User,row.user_id)
        if not user or not auth.live_user(user) or not auth.allowed_in_group(permission.code,'functional'):
            excluded.append({'source_id':row.id,'reason':'individual_grant_requires_functional_review'});continue
        group_id=_id(org_id,'individual',row.id);gp_id=_id(row.id,'permission');ug_id=_id(row.id,'membership')
        if (db.get(GroupPermission,gp_id) and db.get(GroupPermission,gp_id).status!='open') or (db.get(UserGroup,ug_id) and db.get(UserGroup,ug_id).status!='open'):continue
        groups.append({'id':group_id,'code':'MIG-I-'+row.id[:30],'name_ar':'ترحيل منح فردي','scope':'functional',
            'effective_from':str(row.effective_from),'permissions':[permission_item(row,permission,'legacy_individual',{'user_permission_id':row.id},gp_id)],
            'memberships':[{'id':ug_id,'user_id':user.id,**_dates(row),'source_type':'legacy_individual','source_reference':{'user_permission_id':row.id}}]})
    return {'kind':'migration','organization_id':org_id,'source_digest':sha256(auth.canonical(_source(db,org_id))).hexdigest(),
        'groups':groups,'excluded':excluded}


def preview_configuration(db, org_id, group_id, permission_ids, membership_user_ids=()):
    group=db.get(Group,group_id)
    if not group or group.organization_id!=org_id or group.status!='open':raise ValueError('Open group in this organization required')
    permissions=[]
    for permission_id in sorted(set(permission_ids)):
        permission=db.get(Permission,permission_id)
        if not permission or not auth.allowed_in_group(permission.code,group.management_scope):raise ValueError('Permission incompatible with group scope')
        old=db.scalar(select(GroupPermission).where(GroupPermission.group_id==group.id,GroupPermission.permission_id==permission_id,GroupPermission.status=='open'))
        permissions.append({'id':old.id if old else _id(org_id,group_id,permission_id,sha256(auth.canonical(_source(db,org_id))).hexdigest()),
            'permission_id':permission.id,'code':permission.code,**(_dates(old) if old else {'effective_from':str(date.today()),'effective_to':None}),
            'source_type':'institution_configuration','source_reference':{'group_id':group.id}})
    memberships=[]
    for user_id in sorted(set(membership_user_ids)):
        user=db.get(User,user_id)
        if not auth.live_user(user) or user.organization_id!=org_id:raise ValueError('Active institution user required for reviewed assignment')
        old=db.scalar(select(UserGroup).where(UserGroup.group_id==group.id,UserGroup.user_id==user_id,UserGroup.status=='open'))
        memberships.append({'id':old.id if old else _id(org_id,group.id,'membership',user_id,sha256(auth.canonical(_source(db,org_id))).hexdigest()),
            'user_id':user_id,**(_dates(old) if old else {'effective_from':str(date.today()),'effective_to':None}),
            'source_type':'institution_configuration','source_reference':{'group_id':group.id,'user_id':user_id}})
    return {'kind':'configuration','organization_id':org_id,'source_digest':sha256(auth.canonical(_source(db,org_id))).hexdigest(),
        'groups':[{'id':group.id,'code':group.code,'name_ar':group.name_ar,'scope':group.management_scope,'effective_from':str(group.effective_from),
            'permissions':permissions,'memberships':memberships}],'excluded':[]}


def _apply_plan(db, actor_id, envelope):
    from mcias.services import rbac_service as rbac
    with rbac._atomic(db):
        manifest=envelope['manifest'];org_id=manifest['organization_id']
        actor=db.scalar(select(User).where(User.id==actor_id).with_for_update())
        if not auth.technical_admin(db,actor) or actor.organization_id!=org_id:raise ValueError('Independent MFA-enabled technical administrator in same organization required')
        if db.scalar(select(Organization).where(Organization.id==org_id).with_for_update()) is None:raise ValueError('Organization does not exist')
        approver=db.get(User,envelope['approved_by'])
        if not auth.live_user(approver) or approver.organization_id!=org_id or auth.technical_identity(db,approver) or approver.id==actor.id:raise ValueError('Independent institution approver required')
        reference=envelope['approval_reference']
        if not isinstance(reference,str) or not reference.strip() or len(reference)>200:raise ValueError('Institutional approval reference required')
        document=auth.signed_document(manifest,approver.id,reference)
        fingerprint=sha256(document).hexdigest()
        row=RbacProvisioning(organization_id=org_id,applied_by=actor.id,approved_by=approver.id,
            approval_reference=reference,manifest=manifest,fingerprint=fingerprint,signature=envelope['signature'])
        if not auth.valid_provisioning(row):raise ValueError('Invalid or untrusted institutional signature')
        existing=db.scalar(select(RbacProvisioning).where(RbacProvisioning.organization_id==org_id,RbacProvisioning.fingerprint==fingerprint))
        if existing:return existing
        if manifest['kind']=='migration':expected=preview_migration(db,org_id)
        elif manifest['kind']=='configuration':
            if len(manifest['groups'])!=1:raise ValueError('One group configuration per approval')
            target=manifest['groups'][0]
            expected=preview_configuration(db,org_id,target['id'],[p['permission_id'] for p in target['permissions']],[m['user_id'] for m in target['memberships']])
        else:raise ValueError('Unsupported approval plan')
        # Reviewed migration may omit sources; it cannot change identities or add grants.
        if manifest['source_digest']!=expected['source_digest']:raise ValueError('Stale source snapshot; obtain a new review')
        expected_groups={g['id']:g for g in expected['groups']};seen=set()
        for definition in manifest['groups']:
            if definition['id'] in seen or definition['id'] not in expected_groups:raise ValueError('Invalid or duplicate group in plan')
            seen.add(definition['id']);source=expected_groups[definition['id']]
            for field in ('code','scope','name_ar','effective_from'):
                if definition[field]!=source[field]:raise ValueError('Reviewed group definition differs from source')
            for field in ('permissions','memberships'):
                valid={auth.canonical(item) for item in source[field]}
                if len({item['id'] for item in definition[field]})!=len(definition[field]) or any(auth.canonical(item) not in valid for item in definition[field]):raise ValueError('Grant differs from reviewed source')
        db.add(row);db.flush()
        for definition in manifest['groups']:
            group=db.get(Group,definition['id'])
            if group is None:
                group=Group(id=definition['id'],organization_id=org_id,code=definition['code'],name_ar=definition['name_ar'],
                    management_scope=definition['scope'],effective_from=date.fromisoformat(definition['effective_from']),created_by=actor.id)
                db.add(group);db.flush()
            if manifest['kind']=='configuration':
                desired={p['permission_id'] for p in definition['permissions']}
                for old in db.scalars(select(GroupPermission).where(GroupPermission.group_id==group.id,GroupPermission.status=='open')):
                    if old.permission_id not in desired:
                        if old.effective_from>date.today():raise ValueError('Future grant removal needs a separately reviewed lifecycle change')
                        rbac._close(old,actor,'Institutional configuration: '+reference,date.today())
                db.flush()
            for field,model,key in (('permissions',GroupPermission,'group_permission_id'),('memberships',UserGroup,'user_group_id')):
                for item in definition[field]:
                    record=db.get(model,item['id'])
                    if record is None:
                        kwargs={'permission_id':item['permission_id'],'granted_by':actor.id} if field=='permissions' else {'user_id':item['user_id'],'added_by':actor.id}
                        record=model(id=item['id'],organization_id=org_id,group_id=group.id,
                            effective_from=date.fromisoformat(item['effective_from']),effective_to=date.fromisoformat(item['effective_to']) if item['effective_to'] else None,**kwargs)
                        db.add(record);db.flush()
                    if db.scalar(select(RbacGrantOrigin.id).where(getattr(RbacGrantOrigin,key)==record.id)) is None:
                        db.add(RbacGrantOrigin(organization_id=org_id,provisioning_id=row.id,actor_id=actor.id,
                            source_type=item['source_type'],source_reference=item['source_reference'],**{key:record.id}))
        db.flush()
        rbac._audit(db,actor,'rbac.provision','rbac_provisioning',row,after={'fingerprint':fingerprint,'approved_by':approver.id,'approval_reference':reference,'groups':len(manifest['groups'])})
        return row


def apply_plan(db,actor_id,envelope):
    try:
        return _apply_plan(db,actor_id,envelope)
    except (KeyError,TypeError,AttributeError) as exc:
        raise ValueError('Malformed institutional provisioning plan') from exc
