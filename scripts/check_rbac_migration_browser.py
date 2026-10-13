"""Synthetic Chromium -> limited-runtime HTTP -> PostgreSQL RBAC review cycle."""
import argparse,importlib.util,json,os,time
from pathlib import Path
from uuid import uuid4
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from playwright.sync_api import sync_playwright,expect
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from mcias.models import User,Role,UserRole,RolePermission,MFAFactor
from mcias.mfa import generate_totp
from mcias.services import rbac_provisioning as plans,authorization_service as authority
from tests.authorization_fixtures import signed_fixture

ROOT=Path(__file__).resolve().parents[1]

def run(base_url,chromium):
    url=os.environ['MCIAS_E2E_DATABASE_URL']
    if os.getenv('MCIAS_ENVIRONMENT')!='development' or not make_url(url).database.endswith('_e2e'):
        raise ValueError('Explicit development and dedicated synthetic *_e2e database required')
    server_key=bytes.fromhex(os.environ['MCIAS_MFA_ENCRYPTION_KEY'])
    spec=importlib.util.spec_from_file_location('rbac_browser_fixture',ROOT/'tests/api/conftest.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    patch=pytest.MonkeyPatch();generator=module.api_factory.__wrapped__(patch,module.synthetic_password_hash.__wrapped__())
    try:
        api=next(generator)(url=url)
        with Session(api.engine) as db:
            factor=db.scalar(select(MFAFactor).where(MFAFactor.user_id==api.ids['root']))
            nonce=os.urandom(12);factor.encrypted_secret=nonce+AESGCM(server_key).encrypt(nonce,api.mfa_secret,api.ids['root'].encode())
            legacy=Role(code='SYN-browser-reviewed-'+uuid4().hex);db.add(legacy);db.flush()
            db.add_all([UserRole(user_id=api.ids['none'],role_id=legacy.id),RolePermission(role_id=legacy.id,permission_id=api.permissions['claims.read'])]);db.commit()
            manifest=plans.preview_migration(db,api.organization_id)
            envelope=signed_fixture(db,api.ids['root'],manifest)
        errors=[];checks=[];violations=[];output=ROOT/'.e2e-output';output.mkdir(exist_ok=True)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=chromium,args=['--no-sandbox'] if chromium else [])
            page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda error:errors.append(str(error)))
            request=page.request
            assert request.get(base_url+'/api/v1/admin/rbac/migration-preview').status==401
            assert request.get(base_url+'/api/v1/admin/rbac/migration-preview',headers=api.headers['admin']).status==403
            me=request.get(base_url+'/api/v1/permissions/me',headers=api.headers['none']).json()
            assert 'claims.read' not in me['permission_codes']
            wrong={**envelope,'signature':'0'*128}
            assert request.post(base_url+'/api/v1/admin/rbac/apply',headers=api.headers['root'],data=wrong).status==409
            checks.append('anonymous, institution-admin and invalid-signature denial; unreviewed legacy grants inactive')
            page.goto(base_url+'/admin/rbac-migration')
            page.get_by_label('اسم المستخدم',exact=True).fill(api.root_username)
            page.get_by_label('كلمة المرور',exact=True).fill(api.password)
            page.get_by_label('رمز التحقق (إلزامي للإدارة)',exact=True).fill(generate_totp(api.mfa_secret,int(time.time())//30))
            page.get_by_role('button',name='تسجيل الدخول بأمان',exact=True).click()
            expect(page.get_by_role('button',name='تنزيل خطة المراجعة',exact=True)).to_be_visible()
            with page.expect_download() as download:page.get_by_role('button',name='تنزيل خطة المراجعة',exact=True).click()
            downloaded=json.loads(Path(download.value.path()).read_text())
            assert downloaded['source_digest']==manifest['source_digest']
            page.locator('#rbac-signed-plan').set_input_files({'name':'synthetic-reviewed-plan.json','mimeType':'application/json','buffer':json.dumps(envelope).encode()})
            page.get_by_role('button',name='التحقق وتطبيق الترحيل',exact=True).click()
            with page.expect_response(lambda response:response.url.endswith('/api/v1/admin/rbac/apply')) as response:
                page.get_by_role('button',name='تأكيد الإجراء',exact=True).click()
            assert response.value.status==201
            review_id=response.value.json()['id']
            expect(page.locator('main')).to_contain_text('تم التطبيق. معرّف المراجعة')
            me=request.get(base_url+'/api/v1/permissions/me',headers=api.headers['none']).json()
            assert 'claims.read' in me['permission_codes']
            repeat=request.post(base_url+'/api/v1/admin/rbac/apply',headers=api.headers['root'],data=envelope)
            assert repeat.status==201 and repeat.json()['id']==review_id
            checks.append('real MFA login, preview download, signed-plan upload, activation and idempotent replay')
            root_codes=request.get(base_url+'/api/v1/permissions/me',headers=api.headers['root']).json()['permission_codes']
            assert not authority.FINANCIAL_APPROVALS.intersection(root_codes)
            group_path=base_url+f"/api/v1/groups/{api.groups['claims_approver']}/members"
            assert request.post(group_path,headers=api.headers['root'],data={'user_id':api.ids['limited']}).status==403
            assert request.post(group_path,headers=api.headers['admin'],data={'user_id':api.ids['admin']}).status==409
            assert request.post(group_path,headers=api.headers['admin'],data={'user_id':api.ids['limited']}).status==201
            assert 'governance.approve' in request.get(base_url+'/api/v1/permissions/me',headers=api.headers['limited']).json()['permission_codes']
            assert request.post(group_path+'/'+api.ids['limited']+'/remove',headers=api.headers['admin'],data={'reason':'SYN-end assignment'}).status==200
            assert 'governance.approve' not in request.get(base_url+'/api/v1/permissions/me',headers=api.headers['limited']).json()['permission_codes']
            checks.append('technical finance denial, self-assignment denial, institutional staff assignment and immediate revocation')
            page.screenshot(path=str(output/'rbac-migration-ar-light.png'),full_page=True)
            axe=ROOT/'node_modules/axe-core/axe.min.js'
            if axe.is_file():
                page.evaluate(axe.read_text());result=page.evaluate('async()=>await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}})')
                violations=[{'id':v['id'],'targets':[n['target'] for n in v['nodes']]} for v in result['violations']]
            page.get_by_role('button',name='EN',exact=True).click();page.get_by_role('button',name='Theme',exact=True).click()
            expect(page.get_by_role('button',name='Download review plan',exact=True)).to_be_visible()
            for width in (1440,768,390):
                page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                page.screenshot(path=str(output/f'rbac-migration-en-dark-{width}.png'),full_page=True)
            checks.append('Arabic/English, RTL/LTR, light/dark, desktop/tablet/mobile and WCAG checks')
            browser.close()
        assert not errors,errors
        assert not violations,violations
        report={'checks':checks,'actual_http_and_postgresql':True,'synthetic':True,'production_accepted':False,'page_errors':errors,'accessibility_violations':violations}
        (output/'rbac-migration-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps(report,ensure_ascii=False))
    finally:generator.close();patch.undo()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8000');parser.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'))
    args=parser.parse_args();run(args.base_url,args.chromium)
