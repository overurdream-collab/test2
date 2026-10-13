"""Explicit laptop-only institutional admin fixture, never customer provisioning."""
import base64, os, secrets
from datetime import date
from sqlalchemy import select
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from mcias.models import AuditLog, Group, GroupPermission, Permission, User, UserGroup, MFAFactor
from mcias.seed.loader import identifier
from mcias.security import hash_password
from mcias.services import authorization_service as authority, feature_service as features
from mcias.services.rbac_seed import seed_organization, get_default_groups

USERNAME = 'SYN-laptop-institution-admin'


def ensure_admin(db, org_id, accounts, env, operational_permissions):
    from mcias.seed.laptop import guard
    guard(env)
    if db.get_bind().dialect.name != 'postgresql' or db.get_bind().url.database != 'mcias_laptop_e2e':
        raise ValueError('Dedicated laptop PostgreSQL database required')
    if any(account['username'] == USERNAME for account in accounts):
        # Repeated setup must not recreate accounts or restore revoked grants.
        return False
    if db.get(User, identifier('laptop-institution-admin')) or db.scalar(select(User.id).where(User.username == USERNAME)):
        raise ValueError('Institution admin exists without private credentials; operator recovery required')
    root = db.get(User, next(account['id'] for account in accounts if account['username'] == 'SYN-laptop-admin'))
    seed_organization(db, org_id, root.id)
    password = secrets.token_urlsafe(24)
    user = User(id=identifier('laptop-institution-admin'), organization_id=org_id, username=USERNAME,
        full_name_ar='مدير الجهة — حساب اختبار', full_name_en='Institution admin — test account',
        password_hash=hash_password(password))
    db.add(user); db.flush()
    secret = secrets.token_bytes(20); nonce = os.urandom(12)
    cipher = AESGCM(bytes.fromhex(env['MCIAS_MFA_ENCRYPTION_KEY'])).encrypt(nonce, secret, user.id.encode())
    db.add(MFAFactor(user_id=user.id, encrypted_secret=nonce + cipher, enabled=True))
    group = Group(id=identifier('laptop-institution-admin-group'), organization_id=org_id,
        code='laptop_institution_admin', name_ar='مدير الجهة', name_en='Institution administrator',
        management_scope='institution_admin', effective_from=date.today(), created_by=root.id)
    db.add(group); db.flush()
    template = next(g for g in get_default_groups() if g['code'] == 'admin')
    codes = set(template['permissions']) | {c for c in operational_permissions if authority.allowed_in_group(c, 'institution_admin')}
    for code in sorted(codes):
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code); db.add(permission); db.flush()
        db.add(GroupPermission(organization_id=org_id, group_id=group.id, permission_id=permission.id,
            effective_from=date.today(), granted_by=root.id))
    db.add(UserGroup(organization_id=org_id, user_id=user.id, group_id=group.id,
        effective_from=date.today(), added_by=root.id)); db.flush()
    # Initial test entitlements only. Later revocation is never undone by setup.
    for feature in features.list_features(db):
        if feature.is_container or feature.code.startswith('system.'):
            continue
        from mcias.models_features import OrganizationFeature
        if db.scalar(select(OrganizationFeature.id).where(OrganizationFeature.organization_id == org_id,
                OrganizationFeature.feature_code == feature.code, OrganizationFeature.status == 'open')) is None:
            features.grant_feature(db, org_id, feature.code, root.id)
    accounts.append({'id':user.id, 'username':user.username, 'password':password,
        'totp_secret_base32':base64.b32encode(secret).decode().rstrip('=')})
    db.add(AuditLog(actor_id=root.id, organization_id=org_id, action='synthetic_institution_admin_bootstrap',
        resource_type='user', resource_id=user.id, details={'synthetic':True, 'group_id':group.id}))
    return True
