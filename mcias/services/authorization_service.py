"""One functional authority: reviewed group grants and reviewed memberships.

Legacy roles identify technical administrators only. Their permission grants and
individual UserPermission rows are never consulted for authorization.
"""
from datetime import date
import hashlib,json,os
from pathlib import Path
from sqlalchemy import or_,select
from sqlalchemy.orm import aliased
from mcias.models import Group,GroupPermission,UserGroup,UserRole,Role,MFAFactor,Permission,User
from mcias.models_authorization import RbacGrantOrigin,RbacProvisioning
from mcias.authorization_signatures import verify_written_authorization

FINANCIAL_APPROVALS=frozenset({'governance.approve','claims.approve','claims.reject','policies.approve',
    'policies.review','policies.revoke','reference.approve','reference.contracts.approve','rules.activate',
    'intelligence.studio.activate'})
TECHNICAL_ONLY=frozenset({'groups.create','groups.update','groups.close','groups.permissions.grant',
    'groups.permissions.revoke','users.permissions.grant','users.permissions.revoke','permissions.assign'})
ADMIN_ONLY=frozenset({'users.create','users.update','users.close','users.reset_password','users.mfa.manage',
    'groups.members.add','groups.members.remove'})
TECHNICAL_CAPABILITIES=TECHNICAL_ONLY|frozenset({'profile.read','users.read','users.create','users.close','groups.read',
    'groups.members.remove','permissions.read','system.read','system.health.read','system.audit_log.read',
    'system.audit_log.export','system.feature_flags.manage'})

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def live_user(user,today=None):
    today=today or date.today()
    return bool(user and getattr(user,'active',False) and getattr(user,'status',None)=='open' and getattr(user,'effective_from',None)
        and user.effective_from<=today and (user.effective_to is None or user.effective_to>today))

def live(model,today):
    return (model.status=='open',model.effective_from<=today,
        or_(model.effective_to.is_(None),model.effective_to>today))

def technical_identity(db,user):
    if not user:return False
    return bool(user.is_super_admin or db.scalar(select(Role.id).join(UserRole,UserRole.role_id==Role.id)
        .where(UserRole.user_id==user.id,Role.code=='super_admin').limit(1)))

def technical_admin(db,user):
    return live_user(user) and bool(db.scalar(select(Role.id).join(UserRole,UserRole.role_id==Role.id).where(UserRole.user_id==user.id,Role.code=='super_admin').limit(1))) and db.scalar(select(MFAFactor.user_id)
        .where(MFAFactor.user_id==user.id,MFAFactor.enabled.is_(True)).limit(1)) is not None

def allowed_in_group(code,scope):
    if code in TECHNICAL_ONLY or code.startswith(('system.','organizations.')):return False
    if scope=='institution_admin' and code in FINANCIAL_APPROVALS:return False
    if code in ADMIN_ONLY and scope!='institution_admin':return False
    return True

def trust_registry():
    location=os.getenv('MCIAS_RBAC_TRUST_REGISTRY','')
    if not location:return {}
    try:
        path=Path(location)
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o022:return {}
        data=json.loads(path.read_text(encoding='utf-8'))
        return data.get('trusted_approvers',{}) if isinstance(data,dict) else {}
    except (OSError,ValueError,TypeError):return {}

def signed_document(manifest,approver_id,approval_reference):
    return canonical({'purpose':'mcias-rbac-v1','manifest':manifest,'approved_by':approver_id,
        'approval_reference':approval_reference})

def valid_provisioning(row,registry=None):
    try:
        if row.applied_by==row.approved_by or row.manifest['organization_id']!=row.organization_id:return False
        document=signed_document(row.manifest,row.approved_by,row.approval_reference)
        if hashlib.sha256(document).hexdigest()!=row.fingerprint:return False
        key=bytes.fromhex((registry if registry is not None else trust_registry())[row.organization_id][row.approved_by])
        return verify_written_authorization(document,row.fingerprint,row.signature,key)
    except (KeyError,TypeError,ValueError):return False

def _covered(origin,provisioning,group,record,kind,permission_code=None):
    for definition in provisioning.manifest.get('groups',[]):
        if definition['id']!=group.id or definition['scope']!=group.management_scope:continue
        if kind=='membership' and origin.source_type=='institution_assignment':
            return origin.source_reference.get('group_id')==group.id and origin.source_reference.get('user_id')==record.user_id
        for item in definition['permissions' if kind=='permission' else 'memberships']:
            if item['id']!=record.id:continue
            if item['effective_from']!=str(record.effective_from) or item.get('effective_to')!=(str(record.effective_to) if record.effective_to else None):return False
            if kind=='permission':return item['permission_id']==record.permission_id and item['code']==permission_code
            return item['user_id']==record.user_id
    return False

def permission_records(db,user,code=None):
    if not live_user(user) or not user.organization_id:return []
    gp_origin=aliased(RbacGrantOrigin);ug_origin=aliased(RbacGrantOrigin)
    gp_provision=aliased(RbacProvisioning);ug_provision=aliased(RbacProvisioning)
    query=select(Permission,Group,GroupPermission,UserGroup,gp_origin,ug_origin,gp_provision,ug_provision).join(
        GroupPermission,GroupPermission.permission_id==Permission.id).join(Group,Group.id==GroupPermission.group_id).join(
        UserGroup,UserGroup.group_id==Group.id).join(gp_origin,gp_origin.group_permission_id==GroupPermission.id).join(
        ug_origin,ug_origin.user_group_id==UserGroup.id).join(gp_provision,gp_provision.id==gp_origin.provisioning_id).join(
        ug_provision,ug_provision.id==ug_origin.provisioning_id).where(UserGroup.user_id==user.id,
        Group.organization_id==user.organization_id,GroupPermission.organization_id==user.organization_id,
        UserGroup.organization_id==user.organization_id,gp_origin.organization_id==user.organization_id,
        ug_origin.organization_id==user.organization_id,gp_provision.organization_id==user.organization_id,
        ug_provision.organization_id==user.organization_id,*live(Group,date.today()),
        *live(GroupPermission,date.today()),*live(UserGroup,date.today()))
    if code:query=query.where(Permission.code==code)
    registry=trust_registry();verified={};results={};technical=technical_identity(db,user)
    for permission,group,gp,ug,gpo,ugo,gpp,ugp in db.execute(query):
        if not allowed_in_group(permission.code,group.management_scope):continue
        if technical and (permission.code in FINANCIAL_APPROVALS or permission.code=='groups.members.add'):continue
        for provision in (gpp,ugp):
            if provision.id not in verified:verified[provision.id]=valid_provisioning(provision,registry)
        if not verified[gpp.id] or not verified[ugp.id]:continue
        if not _covered(gpo,gpp,group,gp,'permission',permission.code) or not _covered(ugo,ugp,group,ug,'membership'):continue
        results[permission.id]=permission
    return sorted(results.values(),key=lambda p:p.code)

def check_permission_unified(db,user,code):
    if not live_user(user) or not user.organization_id:return False
    if technical_identity(db,user) and (code in FINANCIAL_APPROVALS or code=='groups.members.add'):return False
    if code in TECHNICAL_CAPABILITIES and technical_admin(db,user):return True
    return bool(permission_records(db,user,code))

def permission_codes(db,user):
    codes={p.code for p in permission_records(db,user)}
    if technical_admin(db,user):codes.update(TECHNICAL_CAPABILITIES)
    return sorted(codes)

def institution_admin(db,user):
    return not technical_identity(db,user) and check_permission_unified(db,user,'users.create') and check_permission_unified(db,user,'groups.members.add')
