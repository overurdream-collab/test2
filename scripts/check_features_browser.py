"""Feature management Chromium checks against real HTTP API; fixture stays private."""
import argparse, json, os, time
from pathlib import Path
from urllib.request import Request, urlopen
from playwright.sync_api import sync_playwright, expect
from mcias.mfa import generate_totp

p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8087');p.add_argument('--fixture',required=True)
p.add_argument('--output',default='.e2e-output/features');p.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'))
args=p.parse_args();fixture=json.loads(Path(args.fixture).read_text());out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
checks=[];errors=[]
base=f"/api/v1/organizations/{fixture['organization_id']}/features"
request=Request(args.base_url+base,headers=fixture['headers']['root'])
with urlopen(request) as response: state=json.load(response)
if state['items']:
    request=Request(args.base_url+base,data=json.dumps({'codes':[],'expected_revision':state['revision'],'reason':'Reset isolated browser scenario'}).encode(),
        headers={**fixture['headers']['root'],'Content-Type':'application/json'},method='PUT')
    with urlopen(request) as response: assert response.status==200
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'] if args.chromium else [])
    page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(args.base_url+'/admin/features')
    page.get_by_label('اسم المستخدم',exact=True).fill(fixture['username'])
    page.get_by_label('كلمة المرور',exact=True).fill(fixture['password'])
    page.get_by_label('رمز التحقق (إلزامي للإدارة)',exact=True).fill(generate_totp(bytes.fromhex(fixture['mfa_secret']),int(time.time())//30))
    page.get_by_role('button',name='تسجيل الدخول بأمان',exact=True).click()
    expect(page.locator('.feature-branch')).to_have_count(11)
    page.get_by_label('الجهة',exact=True).select_option(fixture['organization_id'])
    expect(page.locator('.feature-choice')).to_have_count(33)
    page.locator('[data-feature="inputs.contracts"]').check()
    assert page.locator('#feature-parent-inputs').evaluate('(e)=>e.indeterminate')
    page.get_by_role('button',name='حفظ',exact=True).click()
    expect(page.locator('#toast')).to_contain_text('تم حفظ')
    response=page.request.get(args.base_url+f"/api/v1/organizations/{fixture['organization_id']}/features",headers=fixture['headers']['root'])
    assert [r['feature_code'] for r in response.json()['items']]==['inputs.contracts']
    checks.append('real MFA login, 11 containers, 33 leaves and atomic entitlement save')
    page.locator('[data-feature="inputs.caps"]').check();page.get_by_role('button',name='إلغاء',exact=True).click()
    expect(page.locator('[data-feature="inputs.caps"]')).not_to_be_checked();checks.append('cancel reloads persisted feature state')
    page.locator('[data-feature="inputs.contracts"]').uncheck()
    page.get_by_role('button',name='حفظ',exact=True).click()
    assert page.get_by_label('سبب سحب الميزات',exact=True).evaluate('(e)=>!e.validity.valid')
    page.get_by_label('سبب سحب الميزات',exact=True).fill('Synthetic browser revoke')
    page.get_by_role('button',name='حفظ',exact=True).click();expect(page.locator('[data-feature="inputs.contracts"]')).not_to_be_checked()
    checks.append('revocation requires reason and closes the grant')
    page.locator('[data-feature="inputs.contracts"]').check();page.get_by_role('button',name='حفظ',exact=True).click()
    expect(page.locator('#toast')).to_contain_text('تم حفظ')
    page.screenshot(path=str(out/'features-management-ar.png'),full_page=True)
    page.get_by_role('button',name='EN',exact=True).click();expect(page.locator('html')).to_have_attribute('dir','ltr')
    expect(page.get_by_label('Organization',exact=True)).to_be_visible()
    page.get_by_role('button',name='Theme',exact=True).click();page.screenshot(path=str(out/'features-management-en-dark.png'),full_page=True)
    for width in [768,390]:
        page.set_viewport_size({'width':width,'height':844})
        page.screenshot(path=str(out/f'features-{width}.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), page.evaluate('Array.from(document.querySelectorAll("main *")).filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width})).slice(0,12)')
    checks.append('Arabic/English, light/dark and responsive feature tree')
    browser.close()
assert not errors,errors
result={'checks':checks,'page_errors':errors,'synthetic':True,'actual_http_and_postgresql':True}
(out/'management-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
