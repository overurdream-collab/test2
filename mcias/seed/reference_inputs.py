"""Idempotent temporary reference proposals in the dedicated synthetic laptop DB.

No accounts receive functional grants. No source is overwritten and no financial
policy, contract approval, diagnosis or production acceptance is manufactured.
"""
from datetime import date
import os
from sqlalchemy import select
from mcias.models import Organization
from mcias.schemas.registry import SCHEMAS, RecordCreate
from mcias.services import registry_service as registry, feature_service as features


def seed_reference_inputs(db, actor):
    organization=db.get(Organization,actor.organization_id)
    if (os.getenv('MCIAS_ENVIRONMENT','development')!='development'
        or os.getenv('MCIAS_LAPTOP_TEST_MODE')!='synthetic_localhost'
        or not organization or not organization.name.startswith('SYN-')
        or not features.is_super_admin(db,actor)):
        raise ValueError('Explicit synthetic organization and MFA super-admin required')
    created=0;today=date.today()
    titles={
        'inputs.contracts':'SYN عقد مقدم الخدمة', 'inputs.insurers':'SYN شركة التأمين',
        'inputs.regulations':'SYN لائحة مالية', 'inputs.exceptions':'SYN استثناء موثق',
        'inputs.approvals':'SYN موافقة سابقة', 'inputs.caps':'SYN سقف تجريبي',
        'inputs.coverage':'SYN تغطية تجريبية', 'beneficiaries.names':'SYN مستفيد تجريبي',
        'beneficiaries.categories':'SYN الفئة B', 'beneficiaries.cost_sharing':'SYN تحمل الفئة B',
        'providers.hospitals':'SYN مستشفى تجريبي', 'providers.clinics':'SYN عيادة تجريبية',
        'providers.labs':'SYN مختبر تجريبي', 'providers.radiology':'SYN مركز أشعة',
        'providers.pharmacies':'SYN صيدلية تجريبية', 'providers.services':'SYN خدمة كشف',
        'providers.prices':'SYN تسعيرة وحدة قبل التحمل',
    }
    for feature,fields in SCHEMAS.items():
        if not features.check_feature(db,actor.organization_id,feature):
            features.grant_feature(db,actor.organization_id,feature,actor.id)
        values={key:'SYN-REFERENCE' for key in fields}
        values['record_code']='SYN-WORKSPACE-'+feature
        for key,value in {'provider_code':'SYN-HOSPITAL','contract_number':'SYN-CONTRACT-2026',
            'insurer_code':'SYN-INSURER','beneficiary_token':'SYN-BENEFICIARY-B','category_code':'B',
            'service_code':'SYN-VISIT','coding_system':'LOCAL','currency':'LYD','amount':'100.00',
            'percent':'20','scope':'SYN-test-only','document_number':'SYN-DOC-1'}.items():
            if key in values:values[key]=value
        if feature.startswith('providers.') and feature.split('.')[1] in ('clinics','labs','radiology','pharmacies'):
            values['provider_code']='SYN-'+feature.split('.')[1].upper()
        existing=registry.list_records(db,actor,feature,limit=10000)['items']
        if any(r['values']['record_code']==values['record_code'] for r in existing):continue
        registry.create_record(db,actor,feature,RecordCreate(title=titles[feature],effective_from=today,
            values=values,body='SYNTHETIC temporary reference proposal; not institutional approval.'))
        created+=1
    from mcias.seed.linked_references import seed_linked_references
    linked=seed_linked_references(db,actor)
    return {'synthetic':True,'records_created':created,'linked_records_created':linked['records_created'],
        'financially_active':False,'permissions_granted':0}
