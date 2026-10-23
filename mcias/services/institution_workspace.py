"""Tenant-scoped operational counts and reviewed employee-group projections.

Only counts leave this service. Intake remains a reference proposal, not an
approved financial policy. Identity sets deduplicate reference versions.
"""
from datetime import date, datetime, timezone
from sqlalchemy import func, select
from mcias.models import Group, GroupPermission, Organization, User, UserGroup
from mcias.models_reference import BeneficiaryEnrollment, ContractVersion
from mcias.models_ingestion import IngestionJob
from mcias.models_authorization import RbacProvisioning
from mcias.services import authorization_service as auth, feature_service as features
from mcias.services import registry_service as registry, rbac_service as rbac

_INTERNAL_SYNTHETIC_HASHES = ('synthetic-no-login', 'synthetic-not-login')


def _enabled(db, actor, code):
    if auth.authority_mode()=='super_admin':
        if features.is_super_admin(db,actor):return True
        from mcias.schemas.registry import SCHEMAS
        if code in SCHEMAS:
            return features.check_feature(db,actor.organization_id,code) and auth.check_permission_unified(db,actor,f'registry.{code}.read')
    return features.check_feature(db, actor.organization_id, code) and features.permitted(
        db, actor, *features.READ_PERMISSIONS[code])


def _current_intake(db, actor, feature, field, today):
    return {row['values'][field] for row in registry.effective_records(db,actor,feature,today)}


def _metric(value=None, status='available', sources=(), method=''):
    return {'value': value, 'status': status, 'sources': list(sources), 'method': method}


def overview(db, actor):
    today = date.today()
    metrics = {key: _metric(status='restricted') for key in ('beneficiaries', 'insurers', 'providers', 'users')}
    if _enabled(db, actor, 'beneficiaries.names'):
        ids = set(db.scalars(select(BeneficiaryEnrollment.beneficiary_token).where(
            BeneficiaryEnrollment.organization_id == actor.organization_id,
            BeneficiaryEnrollment.effective_from <= today, BeneficiaryEnrollment.effective_until > today)))
        ids.update(_current_intake(db, actor, 'beneficiaries.names', 'beneficiary_token', today))
        metrics['beneficiaries'] = _metric(len(ids), sources=('beneficiary_enrollments', 'beneficiaries.names'),
            method='distinct_current_beneficiary_tokens')
    if _enabled(db, actor, 'inputs.insurers'):
        ids = _current_intake(db, actor, 'inputs.insurers', 'insurer_code', today)
        metrics['insurers'] = _metric(len(ids), sources=('inputs.insurers',),
            method='distinct_insurers_with_registered_current_contracts_not_financial_approval')
    provider_features = [f'providers.{kind}' for kind in ('hospitals', 'clinics', 'labs', 'radiology', 'pharmacies')
                         if _enabled(db, actor, f'providers.{kind}')]
    if provider_features:
        ids = set()
        sources = list(provider_features)
        for feature in provider_features:
            ids.update(_current_intake(db, actor, feature, 'provider_code', today))
        if _enabled(db, actor, 'inputs.contracts'):
            ids.update(db.scalars(select(ContractVersion.provider_code).where(
                ContractVersion.organization_id == actor.organization_id, ContractVersion.status == 'approved',
                ContractVersion.effective_from <= today, ContractVersion.effective_until > today)))
            sources.append('contract_versions')
        metrics['providers'] = _metric(len(ids), sources=sources, method='distinct_current_registered_provider_codes')
    if _enabled(db, actor, 'users.list'):
        count = db.scalar(select(func.count()).select_from(User).where(
            User.organization_id == actor.organization_id, User.password_hash.not_in(_INTERNAL_SYNTHETIC_HASHES),
            User.active.is_(True), *rbac._live(User, today)))
        metrics['users'] = _metric(count, sources=('users',), method='active_effective_accounts_excluding_internal_synthetic_signers')
    organization = db.get(Organization, actor.organization_id)
    last_extraction = db.scalar(select(func.max(IngestionJob.created_at)).where(
        IngestionJob.organization_id == actor.organization_id, IngestionJob.status == 'extracted'))
    return {'organization': {'id': organization.id, 'name': organization.name}, 'metrics': metrics,
            'retrieved_at': datetime.now(timezone.utc), 'as_of': today,
            'last_extracted_job_created_at': last_extraction, 'financially_active': False,
            'scope': 'current_organization', 'institutionally_accepted': False}


def assignment_groups(db, actor):
    """Show functional groups with valid institution approval; no group editing."""
    today = date.today()
    approved = set()
    for provision in db.scalars(select(RbacProvisioning).where(RbacProvisioning.organization_id == actor.organization_id)):
        if auth.valid_provisioning(provision):
            approved.update(g['id'] for g in provision.manifest['groups'] if g['scope'] == 'functional')
    return [{'id': g.id, 'name_ar': g.name_ar, 'name_en': g.name_en, 'code': g.code}
            for g in db.scalars(select(Group).where(Group.organization_id == actor.organization_id,
                Group.id.in_(approved), Group.management_scope == 'functional', *rbac._live(Group, today)).order_by(Group.name_ar))]


def user_directory(db, actor, query='', status=None, offset=0, limit=25):
    from mcias.schemas.user import UserRead
    # The dedicated fixture's non-login signing principals are not employees.
    stmt = select(User).where(User.organization_id == actor.organization_id, User.password_hash.not_in(_INTERNAL_SYNTHETIC_HASHES))
    if status:
        stmt = stmt.where(User.status == status)
    if query:
        # Escape literal wildcard input, preserving a bounded, parameterized query.
        stmt = stmt.where(User.username.contains(query, autoescape=True) | User.full_name_ar.contains(query, autoescape=True))
    users = list(db.scalars(stmt.order_by(User.username, User.id).offset(offset).limit(limit + 1)))
    items = []
    for user in users[:limit]:
        memberships = list(db.execute(select(Group.id, Group.name_ar, Group.name_en).join(UserGroup,
            UserGroup.group_id == Group.id).where(UserGroup.user_id == user.id,
            UserGroup.organization_id == actor.organization_id, Group.organization_id == actor.organization_id,
            *rbac._live(UserGroup, date.today()), *rbac._live(Group, date.today()))))
        items.append({**UserRead.model_validate(user).model_dump(),
            'manageable': user.id != actor.id and not auth.technical_identity(db, user),
            'groups': [{'id': row.id, 'name_ar': row.name_ar, 'name_en': row.name_en} for row in memberships]})
    return {'items': items, 'offset': offset, 'limit': limit, 'has_more': len(users) > limit}
