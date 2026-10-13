"""Synthetic institution administrator cycle over real HTTP and PostgreSQL."""
import argparse, importlib.util, json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from uuid import uuid4
from datetime import date
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from playwright.sync_api import sync_playwright, expect
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from mcias.models import User, MFAFactor, Permission, GroupPermission
from mcias.mfa import generate_totp
from mcias.seed.laptop import ADMIN_PERMISSIONS
from mcias.services import authorization_service as authority
from tests.authorization_fixtures import approve_fixture


def run(base_url, chromium):
    url = os.environ['MCIAS_E2E_DATABASE_URL']
    if os.getenv('MCIAS_ENVIRONMENT') != 'development' or not make_url(url).database.endswith('_e2e'):
        raise ValueError('Dedicated synthetic development *_e2e database required')
    key = bytes.fromhex(os.environ['MCIAS_MFA_ENCRYPTION_KEY'])
    spec = importlib.util.spec_from_file_location('institution_browser_fixture', ROOT / 'tests/api/conftest.py')
    fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
    patch = pytest.MonkeyPatch()
    factory = fixture.api_factory.__wrapped__(patch, fixture.synthetic_password_hash.__wrapped__())
    try:
        api = next(factory)(url=url)
        with Session(api.engine) as db:
            manager = db.get(User, api.ids['admin']); username = manager.username
            manager.full_name_ar = 'SYN-مدير الجهة'
            nonce = os.urandom(12)
            db.add(MFAFactor(user_id=manager.id, enabled=True,
                encrypted_secret=nonce + AESGCM(key).encrypt(nonce, api.mfa_secret, manager.id.encode())))
            for code in ADMIN_PERMISSIONS:
                if not authority.allowed_in_group(code, 'institution_admin'):
                    continue
                permission = db.scalar(select(Permission).where(Permission.code == code))
                if permission is None:
                    permission = Permission(code=code); db.add(permission); db.flush()
                if db.scalar(select(GroupPermission.id).where(GroupPermission.group_id == api.groups['admin'],
                        GroupPermission.permission_id == permission.id)) is None:
                    db.add(GroupPermission(organization_id=api.organization_id, group_id=api.groups['admin'],
                        permission_id=permission.id, granted_by=api.ids['root'], effective_from=date.today()))
            db.flush(); approve_fixture(db, api.organization_id, api.ids['root']); db.commit()
        checks=[]; errors=[]; violations=[]; marker=uuid4().hex[:9]
        out=ROOT/'.e2e-output'; out.mkdir(exist_ok=True)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=chromium, args=['--no-sandbox'] if chromium else [])
            page=browser.new_page(viewport={'width':1440, 'height':1050})
            page.on('pageerror', lambda error: errors.append(str(error)))
            request=page.request
            catalog=request.get(base_url+'/api/v1/admin/features', headers=api.headers['root']).json()['items']
            for leaf in catalog:
                if not leaf['is_container'] and not leaf['code'].startswith('system.'):
                    assert request.post(base_url+f"/api/v1/organizations/{api.organization_id}/features/{leaf['code']}/grant",headers=api.headers['root']).status==201
            page.goto(base_url+'/institution/dashboard')
            page.get_by_label('اسم المستخدم', exact=True).fill(username)
            page.get_by_label('كلمة المرور', exact=True).fill(api.password)
            page.get_by_label('رمز التحقق (إلزامي للإدارة)', exact=True).fill(generate_totp(api.mfa_secret, int(time.time())//30))
            page.get_by_role('button',name='تسجيل الدخول بأمان',exact=True).click()
            expect(page.locator('#institution-metrics')).to_be_visible()
            assert page.locator('#sidebar .nav-heading').all_text_contents()==['الرئيسية','المدخلات والبيانات','المطالبات والدفعات','التدقيق والمراجعة','التحليلات','التقارير','مستخدمو الجهة']
            assert page.locator('[data-metric]').count()==5
            expect(page.locator('[data-metric="health"]')).to_contain_text('جاهز')
            checks.append('real institution-manager MFA login, five real metrics and exactly seven navigation sections')

            def navigate(path):
                page.evaluate('(path)=>{history.pushState({},"",path);dispatchEvent(new PopStateEvent("popstate"));}',path)
            def add_record(path, title, values):
                navigate(path)
                expect(page.get_by_role('button',name='إضافة جديد',exact=True)).to_be_visible()
                page.get_by_role('button',name='إضافة جديد',exact=True).click()
                page.get_by_label('الاسم / العنوان',exact=True).fill(title)
                for label,value in values.items(): page.get_by_label(label,exact=True).fill(value)
                page.get_by_role('button',name='حفظ السجل',exact=True).click()
                expect(page.locator('.intake-card').filter(has_text=title)).to_be_visible()
            add_record('/institution/inputs/insurers','SYN-insurer '+marker,
                {'رمز السجل':'SYN-INS-'+marker,'رمز شركة التأمين':'SYN-INSURER-'+marker,'رقم العقد':'SYN-CONTRACT-'+marker})
            add_record('/institution/beneficiaries/names','SYN-beneficiary '+marker,
                {'رمز السجل':'SYN-BEN-'+marker,'معرّف المستفيد':'SYN-PERSON-'+marker,'رمز الفئة':'SYN-CATEGORY'})
            add_record('/institution/providers/hospitals','SYN-provider '+marker,
                {'رمز السجل':'SYN-PROV-'+marker,'رمز مقدم الخدمة':'SYN-HOSPITAL-'+marker})
            navigate('/institution/dashboard')
            expect(page.locator('#institution-metrics')).to_be_visible()
            for name in ('insurers','beneficiaries','providers'):
                assert page.locator(f'[data-metric="{name}"] .kpi-value').inner_text() in ('1','١')
            checks.append('real insurer-contract, beneficiary and provider intake updates server dashboard counts')
            paths=page.locator('#sidebar .nav-link').evaluate_all('(links)=>links.map(l=>new URL(l.href).pathname).filter(p=>p.startsWith("/institution/"))')
            for path in paths:
                navigate(path); expect(page.locator('main h1')).to_be_visible()
                expect(page.locator('main [aria-busy="true"]')).to_have_count(0, timeout=15000)
                assert page.locator('main .error').count()==0, path
            checks.append(f'all {len(paths)} permitted institutional menu pages render without denied or dead workspaces')

            navigate('/institution/users')
            page.get_by_role('button',name='إضافة مستخدم',exact=True).click()
            employee='SYN-staff-'+marker; title='<img src=x onerror=alert(1)> '+employee
            page.get_by_label('اسم المستخدم',exact=True).fill(employee)
            page.get_by_label('الاسم الكامل',exact=True).fill(title)
            page.get_by_label('كلمة المرور الأولية',exact=True).fill(api.password)
            page.get_by_role('button',name='إنشاء الحساب',exact=True).click()
            expect(page.get_by_role('button',name='إسناد فئة معتمدة',exact=True)).to_be_visible()
            assert page.locator('#drawer img').count()==0
            page.get_by_role('button',name='إسناد فئة معتمدة',exact=True).click()
            page.get_by_label('الفئة الوظيفية',exact=True).select_option(label='مشاهد')
            page.get_by_role('button',name='تأكيد الإسناد',exact=True).click()
            row=page.locator('.staff-card').filter(has_text=employee)
            expect(row).to_contain_text('مشاهد')
            assert page.locator('.staff-card img').count()==0
            row.get_by_role('button',name='إدارة الحساب',exact=True).click()
            page.get_by_role('button',name='إزالة الإسناد',exact=True).click()
            page.get_by_label('سبب الإجراء',exact=True).fill('SYN-role ended')
            page.get_by_role('button',name='تنفيذ الإجراء',exact=True).click()
            page.get_by_role('button',name='تأكيد الإجراء',exact=True).click()
            expect(page.locator('#drawer')).not_to_be_visible()
            row.get_by_role('button',name='إدارة الحساب',exact=True).click()
            page.get_by_role('button',name='إغلاق الحساب',exact=True).click()
            page.get_by_label('سبب الإجراء',exact=True).fill('SYN-account ended')
            page.get_by_role('button',name='تنفيذ الإجراء',exact=True).click()
            page.get_by_role('button',name='تأكيد الإجراء',exact=True).click()
            expect(row).to_contain_text('مغلق')
            assert request.post(base_url+'/api/v1/admin/rbac/configuration-preview',headers=api.headers['admin'],data={'group_id':api.groups['viewer'],'permission_ids':[]}).status==403
            codes=request.get(base_url+'/api/v1/permissions/me',headers=api.headers['admin']).json()['permission_codes']
            assert not authority.FINANCIAL_APPROVALS.intersection(codes)
            assert request.post(base_url+f"/api/v1/groups/{api.groups['viewer']}/members",headers=api.headers['admin'],data={'user_id':api.ids['admin']}).status==409
            checks.append('real employee create, approved-group assignment/revocation and closure; XSS-safe rendering and no admin/finance escalation')

            for lang in ('ar','en'):
                if lang=='en':page.get_by_role('button',name='EN',exact=True).click()
                for width in (1440,768,390):
                    page.set_viewport_size({'width':width,'height':1050});navigate('/institution/dashboard')
                    expect(page.locator('#institution-metrics')).to_be_visible()
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(lang,width)
                    if width in (1440,390):
                        page.evaluate((ROOT/'node_modules/axe-core/axe.min.js').read_text())
                        violations.extend(page.evaluate('async()=> (await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa"]}})).violations'))
                    page.screenshot(path=str(out/f'institution-admin-{lang}-{width}.png'),full_page=True)
                page.get_by_role('button',name='الثيم' if lang=='ar' else 'Theme',exact=True).click()
            checks.append('Arabic RTL / English LTR, light/dark, desktop/tablet/mobile and WCAG checks')
            assert not errors and not violations
            browser.close()
        report={'checks':checks,'actual_http_and_postgresql':True,'synthetic':True,'production_accepted':False,
            'page_errors':errors,'accessibility_violations':violations}
        (out/'institution-admin-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(json.dumps(report,ensure_ascii=False))
    finally:
        factory.close();patch.undo()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'))
    args=parser.parse_args();run(args.base_url,args.chromium)
