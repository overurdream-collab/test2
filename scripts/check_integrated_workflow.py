"""Synthetic browser/HTTP lifecycle against a dedicated *_e2e PostgreSQL database.

G5 has no execution HTTP API. The harness inserts ONE explicitly synthetic snapshot
computed by the existing Python engine and independently checked by Palermo-2.
This tests downstream integration, never production policy activation.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from playwright.sync_api import sync_playwright, expect
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from mcias.audit_agents import AGENTS
from mcias.audit_engine import AuditPolicy, evaluate
from mcias.mfa import generate_totp
from mcias.models import Organization, User, Role, Permission, RolePermission, UserRole, MFAFactor, AuditLog
from mcias.models_audit import AuditSnapshot
from mcias.models_claims import ClaimEntry
from mcias.models_ingestion import IngestionDocument
from mcias.palermo2 import verify
from mcias.storage import EncryptedStore
from mcias.models import SourceFile
from mcias.security import hash_password

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'synthetic_workflow_password_only'


def run(base_url, chromium=None):
    (ROOT/'.e2e-output').mkdir(exist_ok=True)
    url = os.environ['MCIAS_E2E_DATABASE_URL']
    if not make_url(url).database.endswith('_e2e'):
        raise ValueError('Dedicated *_e2e database required')
    if os.environ.get('MCIAS_ENVIRONMENT') != 'development':
        raise ValueError('Explicit development environment required')
    engine = create_engine(url)
    unique = uuid4().hex[:12]
    secret = os.urandom(20)
    permissions = ['profile.read', 'claims.read', 'claims.import', 'ingestion.read',
                   'ingestion.upload', 'reports.read', 'reports.create', 'reports.export',
                   'reports.details.read', 'governance.propose', 'governance.approve',
                   'governance.review', 'governance.reaudit']
    ids = {}
    with Session(engine) as db:
        org = Organization(name='SYNTHETIC WORKFLOW ' + unique)
        foreign = Organization(name='SYNTHETIC FOREIGN ' + unique)
        db.add_all([org, foreign]); db.flush()
        organization_id, foreign_organization_id = org.id, foreign.id
        role = Role(code='workflow_' + unique)
        db.add(role); db.flush()
        for code in permissions:
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if permission is None:
                permission = Permission(code=code); db.add(permission); db.flush()
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        for name in ('operator', 'reviewer', 'foreign'):
            user = User(organization_id=foreign.id if name == 'foreign' else org.id,
                        username='workflow-' + name + '-' + unique,
                        password_hash=hash_password(PASSWORD))
            db.add(user); db.flush()
            db.add(UserRole(user_id=user.id, role_id=role.id))
            ids[name] = {'id': user.id, 'username': user.username}
        admin = db.scalar(select(Role).where(Role.code == 'super_admin'))
        if admin is None:
            admin = Role(code='super_admin'); db.add(admin); db.flush()
        db.add(UserRole(user_id=ids['operator']['id'], role_id=admin.id))
        nonce = os.urandom(12)
        encrypted = AESGCM(bytes.fromhex(os.environ['MCIAS_MFA_ENCRYPTION_KEY'])).encrypt(
            nonce, secret, ids['operator']['id'].encode())
        db.add(MFAFactor(user_id=ids['operator']['id'], encrypted_secret=nonce + encrypted, enabled=True))
        db.flush()
        from mcias.seed.authorization import approve_synthetic
        approve_synthetic(db,organization_id,'development')
        approve_synthetic(db,foreign.id,'development')
        db.commit()
    checks = []
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chromium,
                                    args=['--no-sandbox'] if chromium else [])
        page = browser.new_page(viewport={'width':1440, 'height':1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base_url + '/login')
        page.get_by_label('اسم المستخدم', exact=True).fill(ids['operator']['username'])
        page.get_by_label('كلمة المرور', exact=True).fill(PASSWORD)
        page.get_by_label('رمز التحقق (إلزامي للإدارة)', exact=True).fill(generate_totp(secret, int(time.time()) // 30))
        with page.expect_response(lambda r: r.url.endswith('/api/v1/auth/login')) as response:
            page.get_by_role('button', name='تسجيل الدخول بأمان', exact=True).click()
        assert response.value.status == 200
        operator_headers = {'Authorization':'Bearer ' + response.value.json()['access_token']}
        expect(page.locator('main h1')).to_be_visible()
        checks.append('real administrative login with enrolled encrypted MFA')

        def request(method, path, headers=operator_headers, data=None, expected=200):
            result = page.request.fetch(base_url + path, method=method, headers=headers, data=data)
            assert result.status == expected, (method, path, result.status)
            return result.json() if 'json' in result.headers.get('content-type', '') else result.body()

        def navigate(path):
            page.evaluate('(path)=>{history.pushState({},"",path);dispatchEvent(new PopStateEvent("popstate"));}', path)
            expect(page.locator('main h1')).to_be_visible()

        # Explicit fixture entitlements; runtime/default Seed never grants features.
        for code in ('dashboard.summary','claims.list','claims.batches','audit.snapshots','governance.cases','reports.list'):
            request('POST', f'/api/v1/organizations/{organization_id}/features/{code}/grant', expected=201)
        # Exercise tenant isolation after entitlement, rather than failing earlier.
        request('POST', f'/api/v1/organizations/{foreign_organization_id}/features/claims.list/grant', expected=201)

        def upload(data, filename):
            navigate('/admin/ingestion')
            page.get_by_label('المستند المصدر', exact=True).set_input_files({'name':filename, 'mimeType':'text/csv', 'buffer':data})
            with page.expect_response(lambda r: '/api/v1/ingestion/uploads?' in r.url) as response:
                page.get_by_role('button', name='رفع وتسجيل المصدر', exact=True).click()
            assert response.value.status == 200
            return response.value.json()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['claim_reference','beneficiary_token','provider_code','service_code','service_date','claimed_amount','currency','diagnosis'])
        writer.writerow(['SYN-' + unique,'SYN-BENEFICIARY','SYN-PROVIDER','SYN-SERVICE','2026-10-01','200.00','LYD','SYNTHETIC-PRIVATE-DIAGNOSIS'])
        data = output.getvalue().encode()
        uploaded = upload(data, 'synthetic-workflow.csv')
        assert uploaded['status'] == 'extracted'
        assert uploaded['sha256'] == hashlib.sha256(data).hexdigest()
        request('GET', '/api/v1/ingestion/jobs/' + uploaded['job_id'] + '/records', expected=403)
        assert upload(data, 'synthetic-workflow.csv')['status'] == 'duplicate'
        checks.append('browser upload, source hash, extraction, duplicate detection and denied raw medical fields')
        bad = upload(b'not a valid spreadsheet', 'synthetic-invalid.xlsx')
        assert bad['status'] == 'review_required'
        quarantine = request('GET', '/api/v1/ingestion/jobs/' + bad['job_id'] + '/quarantine')
        assert quarantine['items']
        request('POST', '/api/v1/claims/batches/from-document/' + bad['document_id'], expected=409)
        with Session(engine) as db:
            source = db.get(SourceFile, db.get(IngestionDocument, bad['document_id']).source_id)
            store = EncryptedStore(os.environ['MCIAS_STORAGE_DIR'], bytes.fromhex(os.environ['MCIAS_STORAGE_KEY']))
            assert store.get(source.storage_key, source.sha256) == b'not a valid spreadsheet'
        checks.append('malformed source quarantine, encrypted original retained and import blocked')

        navigate('/institution/claims/batches')
        form = page.locator('.form-panel').filter(has=page.get_by_role('heading', name='تجهيز دفعة من مصدر موثّق', exact=True))
        form.get_by_label('المستند', exact=True).fill(uploaded['document_id'])
        with page.expect_response(lambda r: '/batches/from-document/' in r.url) as response:
            form.get_by_role('button', name='تنفيذ الطلب', exact=True).click()
        assert response.value.status == 201
        batch = response.value.json()['id']
        form = page.locator('.form-panel').filter(has=page.get_by_role('heading', name='استئناف استيراد الدفعة', exact=True))
        form.get_by_label('الدفعة', exact=True).fill(batch)
        form.get_by_role('button', name='تنفيذ الطلب', exact=True).click()
        with page.expect_response(lambda r: '/resume?' in r.url) as response:
            page.get_by_role('button', name='تأكيد الإجراء', exact=True).click()
        assert response.value.json()['status'] == 'imported'
        assert request('POST', '/api/v1/claims/batches/' + batch + '/resume')['imported_count'] == 1
        claim_id = request('GET', '/api/v1/claims/batches/' + batch + '/entries')['entries'][0]['id']
        request('POST', '/api/v1/claims/entries/' + claim_id + '/attachments/' + uploaded['document_id'], expected=201)
        checks.append('browser staging and confirmed resumable import without duplicates; evidence linked')
        baseline = request('POST', '/api/v1/reports/batches/' + batch + '/snapshots', expected=201)
        assert baseline['summary']['by_currency']['LYD']['held_count'] == 1

        # Explicit test seam: no audit execution HTTP endpoint or approved policy registry is fabricated.
        with Session(engine) as db:
            claim = db.get(ClaimEntry, claim_id)
            policy = AuditPolicy(policy_id='SYNTHETIC-WORKFLOW-ONLY', currency='LYD', rounding='HALF_UP', precision=2,
                                 order=('exclusion','tariff','cap','copay'), exclusion=Decimal('10'), tariff=Decimal('100'),
                                 cap=Decimal('80'), copay_percent=Decimal('20'), approved=True)
            calculation = evaluate(claim.claimed_amount, claim.currency, policy, eligible=True, evidence_complete=True,
                                   source_id=claim.extracted_record_id, contract_id='SYNTHETIC-CONTRACT', beneficiary_enrollment_id='SYNTHETIC-ENROLLMENT')
            findings = [{'agent':agent, 'status':'pass', 'reason':'SYNTHETIC TEST FIXTURE', 'reference':uploaded['document_id']} for agent in AGENTS]
            verification = verify(claim, findings, calculation)
            assert verification['status'] == 'verified'
            snapshot = AuditSnapshot(organization_id=claim.organization_id, claim_id=claim.id, policy_id=policy.policy_id,
                                     policy_fingerprint='c'*64, calculation=calculation, findings={'agents':findings},
                                     verification=verification, created_by=ids['operator']['id'])
            db.add(snapshot); db.flush(); snapshot_id = snapshot.id; db.commit()
        navigate('/institution/financial-audit')
        expect(page.locator('tbody tr').first).to_be_visible()
        page.get_by_role('button', name='عرض الدليل', exact=True).first.click()
        expect(page.locator('#drawer .finding')).to_have_count(8)
        expect(page.locator('#drawer')).to_contain_text('64.00')
        page.keyboard.press('Escape')
        checks.append('synthetic backend-engine snapshot independently verified and eight-agent browser evidence')
        case = request('POST', '/api/v1/governance/cases/from-audit/' + snapshot_id, expected=201)['id']
        event_path = '/api/v1/governance/cases/' + case + '/events'
        request('POST', event_path, data={'kind':'propose','payload':{}}, expected=201)
        for kind in ('approve','reject'):
            request('POST', event_path, data={'kind':kind,'payload':{}}, expected=403)
        reviewer_token = request('POST','/api/v1/auth/login', headers={}, data={'username':ids['reviewer']['username'],'password':PASSWORD})['access_token']
        reviewer_headers = {'Authorization':'Bearer ' + reviewer_token}
        foreign_token = request('POST','/api/v1/auth/login', headers={}, data={'username':ids['foreign']['username'],'password':PASSWORD})['access_token']
        request('GET', '/api/v1/workspace/claims/' + claim_id, headers={'Authorization':'Bearer ' + foreign_token}, expected=404)
        request('POST', event_path, headers=reviewer_headers, data={'kind':'approve','payload':{}}, expected=201)
        approved = request('POST', '/api/v1/reports/batches/' + batch + '/snapshots', expected=201)
        assert approved['summary']['by_currency']['LYD']['payable'] == '64.00'
        assert request('GET', '/api/v1/reports/snapshots/' + baseline['id'])['summary']['by_currency']['LYD']['payable'] == '0'
        export = request('GET', '/api/v1/reports/snapshots/' + approved['id'] + '/excel')
        assert export[:2] == b'PK'
        request('GET', '/api/v1/reports/snapshots/' + approved['id'] + '/excel?include_originals=true', expected=403)
        checks.append('independent approval, tenant denial, reconciled frozen totals, authorized export and original-field export denied')
        request('POST', event_path, data={'kind':'object','payload':{}}, expected=403)
        request('POST', event_path, data={'kind':'object','payload':{'reason_code':'SYNTHETIC_OBJECTION'},'evidence_document_id':uploaded['document_id']}, expected=201)
        objected = request('POST', '/api/v1/reports/batches/' + batch + '/snapshots', expected=201)
        assert objected['summary']['by_currency']['LYD']['payable'] == '0'
        assert request('GET', '/api/v1/reports/snapshots/' + approved['id'])['fingerprint'] == approved['fingerprint']
        request('POST', event_path, data={'kind':'request_reaudit','payload':{'reason_code':'SYNTHETIC_REVIEW'}}, expected=201)
        history = request('GET', '/api/v1/governance/cases/' + case)
        assert [e['kind'] for e in history['events']] == ['propose','approve','object','request_reaudit']
        with Session(engine) as db:
            actions = set(db.scalars(select(AuditLog.action).where(AuditLog.actor_id.in_([ids['operator']['id'],ids['reviewer']['id']]))))
            assert {'source_ingested','claim_batch_staged','claim_batch_resumed','g6_propose','g6_approve','g6_object','g6_request_reaudit'} <= actions
        checks.append('evidenced objection, re-audit request, immutable prior report and backend action audit trail')
        assert not errors, errors
        browser.close()
    engine.dispose()
    result = {'synthetic_data':True,'actual_http_and_postgresql':True,
              'audit_execution':'fixture seam using Python engine; no production execution API',
              'checks':checks,'page_errors':errors,'institutional_acceptance':False}
    (ROOT/'.e2e-output/integrated-workflow-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url',default='http://127.0.0.1:8002')
    parser.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'))
    args=parser.parse_args()
    run(args.base_url,args.chromium)
