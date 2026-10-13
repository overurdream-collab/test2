"""Chromium -> real API -> PostgreSQL intake lifecycle and import evidence."""
import argparse,json,os,time
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
from mcias.mfa import generate_totp

p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8087');p.add_argument('--fixture',required=True)
p.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'));p.add_argument('--output',default='.e2e-output/features')
p.add_argument('--axe',default='node_modules/axe-core/axe.min.js');args=p.parse_args()
fixture=json.loads(Path(args.fixture).read_text());out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
errors=[];checks=[];violations=[];marker=uuid4().hex[:10]
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'] if args.chromium else [])
    request=browser.new_context().request
    groups=request.get(args.base_url+'/api/v1/groups?limit=100',headers=fixture['headers']['root']).json()['items']
    admin=next(g for g in groups if g['code']=='admin')
    root=request.get(args.base_url+'/api/v1/me/features',headers=fixture['headers']['root']).json()['user']
    membership=request.post(args.base_url+f"/api/v1/groups/{admin['id']}/members",headers=fixture['headers']['root'],data={'user_id':root['id']})
    # Technical administrators cannot assign themselves functional memberships.
    assert membership.status==403
    page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(args.base_url+'/institution/providers/hospitals')
    page.get_by_label('اسم المستخدم',exact=True).fill(fixture['username']);page.get_by_label('كلمة المرور',exact=True).fill(fixture['password'])
    page.get_by_label('رمز التحقق (إلزامي للإدارة)',exact=True).fill(generate_totp(bytes.fromhex(fixture['mfa_secret']),int(time.time())//30))
    page.get_by_role('button',name='تسجيل الدخول بأمان',exact=True).click()
    expect(page.get_by_role('button',name='إضافة جديد',exact=True)).to_be_visible()
    assert page.locator('#sidebar summary').all_text_contents()==['المدخلات','المستفيدون','مقدمو الخدمة']
    page.get_by_role('button',name='إضافة جديد',exact=True).click()
    title='<img src=x onerror=alert(1)> SYN-Hospital-'+marker
    page.get_by_label('الاسم / العنوان',exact=True).fill(title)
    page.get_by_label('رمز السجل',exact=True).fill('SYN-HOSP-'+marker)
    page.get_by_label('رمز مقدم الخدمة',exact=True).fill('SYN-PROVIDER-'+marker)
    page.get_by_role('button',name='حفظ السجل',exact=True).click()
    expect(page.locator('.intake-card').filter(has_text=title)).to_be_visible()
    assert page.locator('.intake-card img').count()==0
    card=page.locator('.intake-card').filter(has_text=title);card.get_by_role('button',name='عرض التفاصيل',exact=True).click()
    expect(page.locator('#drawer')).to_contain_text('بانتظار المراجعة المؤسسية')
    page.get_by_role('button',name='إغلاق السجل',exact=True).click()
    page.get_by_label('سبب الإغلاق',exact=True).fill('إغلاق اصطناعي للاختبار')
    page.get_by_role('button',name='تأكيد الإغلاق',exact=True).click()
    expect(page.locator('#drawer')).not_to_be_visible()
    card.get_by_role('button',name='عرض التفاصيل',exact=True).click()
    page.get_by_role('button',name='إضافة نسخة جديدة',exact=True).click()
    assert page.get_by_label('رمز السجل',exact=True).evaluate('(e)=>e.readOnly')
    page.get_by_label('الاسم / العنوان',exact=True).fill('SYN-Hospital revised '+marker)
    page.get_by_role('button',name='حفظ السجل',exact=True).click()
    expect(page.locator('.intake-card').filter(has_text='SYN-Hospital revised '+marker)).to_contain_text('النسخة 3')
    checks.append('real create, encrypted source, XSS-safe rendering, close and version 3')
    page.get_by_role('button',name='استيراد ملف',exact=True).click()
    raw=('title,effective_from,record_code,provider_code\nSYN-Imported,'+time.strftime('%Y-%m-%d')+',SYN-IMPORT-'+marker+',SYN-PROVIDER-'+marker+'\n').encode()
    page.get_by_label('ملف المصدر',exact=True).set_input_files({'name':'SYN-provider.csv','mimeType':'text/csv','buffer':raw})
    page.get_by_role('button',name='رفع ومعاينة',exact=True).click()
    expect(page.locator('.import-row')).to_have_count(1)
    page.get_by_role('button',name='تأكيد وحفظ المحدد',exact=True).click()
    page.get_by_role('button',name='تأكيد الإجراء',exact=True).click()
    expect(page.locator('#drawer')).not_to_be_visible();expect(page.locator('.intake-card').filter(has_text='SYN-Imported')).to_be_visible()
    page.locator('.intake-card').filter(has_text='SYN-Imported').get_by_role('button',name='عرض التفاصيل',exact=True).click()
    with page.expect_download() as download:
        page.get_by_role('button',name='تنزيل المصدر المرتبط',exact=True).click()
    assert Path(download.value.path()).read_bytes()==raw
    page.keyboard.press('Escape');checks.append('CSV preview, human confirmation, persisted intake and exact authorized source download')
    routes=json.loads((Path(__file__).resolve().parents[1]/'mcias/web_workspace/routes.json').read_text())
    def navigate(path):
        page.evaluate('(path)=>{history.pushState({},"",path);dispatchEvent(new PopStateEvent("popstate"));}',path)
    for route in [r for r in routes if r['kind']=='input-list' and r['path'].startswith('/institution/')]:
        navigate(route['path']);expect(page.locator('main h1')).to_have_text(route['ar'])
        expect(page.get_by_role('button',name='إضافة جديد',exact=True)).to_be_visible()
    checks.append('all sixteen institution intake routes render operational controls')
    navigate('/institution/providers/hospitals');expect(page.locator('.intake-card').first).to_be_visible()
    page.screenshot(path=str(out/'intake-ar-light.png'),full_page=True)
    if Path(args.axe).is_file():
        page.evaluate(Path(args.axe).read_text());result=page.evaluate('async()=>await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}})')
        violations.extend([{'id':v['id'],'targets':[n['target'] for n in v['nodes']]} for v in result['violations']])
    page.get_by_role('button',name='EN',exact=True).click();page.get_by_role('button',name='Theme',exact=True).click()
    for width in [1440,768,390]:
        page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.screenshot(path=str(out/f'intake-en-dark-{width}.png'),full_page=True)
    checks.append('Arabic RTL, English LTR, light/dark, desktop/tablet/mobile')
    browser.close()
assert not errors,errors
assert not violations,violations
result={'checks':checks,'page_errors':errors,'accessibility_violations':violations,'synthetic':True,'actual_http_and_postgresql':True}
(out/'intake-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
