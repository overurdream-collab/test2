"""Real HTTP helpers for isolated synthetic NET cycle and volume verification.

No financial snapshots are fabricated. Policies use real HMAC enrollment and
separate explicitly granted synthetic institutional approver/reviewer accounts.
"""
from datetime import date
from io import BytesIO
import hashlib
import hmac
import secrets
from types import SimpleNamespace
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.models import Permission
from mcias.models_claims import ClaimEntry
from mcias.audit_service import fingerprint_policy
from mcias.services.net_audit_service import decode_policy
from tests.workspace_v2.test_access_and_registry import grants
from tests.workspace_v2.test_linked_references import linked_mapping
from tests.workspace_v2.test_mapping_and_results import upload_batch
from tests.workspace_v2.invoice_fixtures import attach_invoices


HEADERS=['رقم الفاتورة','الرقم التأميني','اسم المستفيد','الدرجة','مقدم الخدمة','الخدمة',
         'تاريخ الخدمة','السعر','المطلوب','نسبة التحمل','إجمالي التحمل','الصافي']


def case_row(index=1,**overrides):
    row={'invoice_reference':f'SYN-CYCLE-{index:06d}','beneficiary':'SYN-INS-EMPLOYEE',
         'name':'SYN موظف تجريبي','category':'B','provider':'SYN-LINKED-HOSPITAL','service':'SYN-VISIT',
         'date':date.today().strftime('%d/%m/%Y'),'unit':'1000','gross':'1000','percent':'10','copay':'100','net':'900'}
    row.update(overrides);return row


def workbook(cases):
    book=Workbook();sheet=book.active;sheet.title='مطالبات دورة اصطناعية';sheet.sheet_view.rightToLeft=True
    sheet.append(HEADERS)
    keys=('invoice_reference','beneficiary','name','category','provider','service','date','unit','gross','percent','copay','net')
    for row in cases:sheet.append([row[key] for key in keys])
    output=BytesIO();book.save(output);return output.getvalue()


def import_cases(api,cases=None,attach=True,missing_references=()):
    cases=cases or [case_row()];raw=workbook(cases)
    batch,document=upload_batch(api,raw,'SYN-net-cycle.xlsx')
    base='/api/v1/claims/batches/'+batch
    response=api.client.put(base+'/mapping',json=linked_mapping(),headers=api.headers['root'])
    assert response.status_code==200,response.text
    while True:
        response=api.client.post(base+'/resume',headers=api.headers['root'])
        assert response.status_code==200,response.text
        if response.json()['status']!='importing':break
    assert response.json()['status']=='imported' and response.json()['imported_count']==len(cases),response.text
    with Session(api.engine) as db:
        claims=list(db.scalars(select(ClaimEntry).where(ClaimEntry.batch_id==batch)))
        identities={claim.claim_reference:claim.id for claim in claims}
        omitted=[claim.id for claim in claims if claim.claim_reference in missing_references]
    invoice_document=invoice_raw=None
    if attach:
        invoice_document,invoice_raw=attach_invoices(api,batch,skip_ids=omitted)
        response=api.client.post(base+'/reference-checks',headers=api.headers['root'])
        assert response.status_code==201,response.text
    return SimpleNamespace(batch_id=batch,document_id=document,raw=raw,cases=cases,identities=identities,
        invoice_document_id=invoice_document,invoice_raw=invoice_raw)


def configure_signers(api,monkeypatch):
    secret=secrets.token_hex(32);monkeypatch.setenv('MCIAS_G5_POLICY_VERIFICATION_KEY',secret)
    codes=('policies.approve','policies.review','policies.revoke','governance.approve')
    with Session(api.engine) as db:
        for code in codes:
            if db.scalar(select(Permission.id).where(Permission.code==code)) is None:
                db.add(Permission(code=code))
        db.commit()
    response=grants(api,['policies.approve','policies.revoke','governance.approve','claims.read'],user='none')
    assert response.status_code==200,response.text
    response=grants(api,['policies.review'],user='viewer')
    assert response.status_code==200,response.text
    api.net_policy_secret=secret;api.net_enrolled={}
    return secret


def approve_batch_policies(api,batch,secret=None,overrides=None):
    secret=secret or api.net_policy_secret
    response=api.client.get(f'/api/v1/audits/batches/{batch}/policy-requirements',headers=api.headers['root'])
    assert response.status_code==200,response.text
    policies={}
    for item in response.json()['items']:
        calc=item['reference_calculation']
        if calc is None:continue
        reference=item['reference_fingerprint']
        definition={'policy_id':'SYN-NET-'+reference[:24],'currency':calc['currency'],
            'rounding':calc['rounding'],'precision':calc['precision'],
            'order':['exclusion','tariff','cap','copay'],'copay_percent':calc['beneficiary_copay_percent'],
            'cap':None,'exclusion':'0','tariff':calc['tariff_unit'],'approved':True,
            'amount_basis':'NET','reference_fingerprint':reference}
        definition.update(overrides or {})
        fingerprint=fingerprint_policy(decode_policy(definition))
        if fingerprint not in api.net_enrolled:
            message='|'.join((api.organization_id,fingerprint,api.ids['none'],api.ids['viewer'])).encode()
            signature=hmac.new(secret.encode(),message,hashlib.sha256).hexdigest()
            request={'organization_id':api.organization_id,'policy_id':definition['policy_id'],
                'policy_fingerprint':fingerprint,'approver_id':api.ids['none'],'reviewer_id':api.ids['viewer'],'signature':signature}
            grant=api.client.post('/api/v1/audit-policies/grants',json=request,headers=api.headers['none'])
            assert grant.status_code==201,grant.text
            recorded=api.client.post('/api/v1/audit-policies/definitions',json=definition,headers=api.headers['none'])
            assert recorded.status_code==201,recorded.text
            api.net_enrolled[fingerprint]={'definition':definition,'grant_id':grant.json()['id'],'fingerprint':fingerprint}
        policies[item['line_id']]=api.net_enrolled[fingerprint]
    return policies


def execute_batch(api,batch):
    response=api.client.post(f'/api/v1/audits/batches/{batch}/run',headers=api.headers['root'])
    assert response.status_code==201,response.text
    return response.json()


def result_files(api,batch):
    response=api.client.post('/api/v1/result-files/batches/'+batch,headers=api.headers['root'])
    assert response.status_code==201,response.text
    result=response.json()
    downloaded=api.client.get('/api/v1/result-files/'+result['id']+'/download',headers=api.headers['root'])
    assert downloaded.status_code==200,downloaded.text
    return result,downloaded.content
