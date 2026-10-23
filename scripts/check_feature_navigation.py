"""Real HTTP feature visibility/revocation checks; no permanent demo grants."""
import argparse,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8087');p.add_argument('--fixture',required=True)
p.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'));p.add_argument('--output',default='.e2e-output/features')
args=p.parse_args();fixture=json.loads(Path(args.fixture).read_text());out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
errors=[];checks=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'] if args.chromium else [])
    request=browser.new_context().request
    base=f"{args.base_url}/api/v1/organizations/{fixture['organization_id']}/features"
    state=request.get(base,headers=fixture['headers']['root']).json()
    assert request.put(base,headers=fixture['headers']['root'],data={'codes':[],'expected_revision':state['revision'],'reason':'Reset isolated navigation case'}).status==200
    actor=request.get(args.base_url+'/api/v1/me/features',headers=fixture['headers']['admin']).json()
    page=browser.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(args.base_url+'/login');page.get_by_label('اسم المستخدم',exact=True).fill(actor['user']['username'])
    page.get_by_label('كلمة المرور',exact=True).fill(fixture['password']);page.get_by_role('button',name='تسجيل الدخول بأمان',exact=True).click()
    expect(page.locator('#sidebar')).to_contain_text('لا ميزات مفعّلة')
    assert page.locator('#sidebar a[href="/institution/claims"]').count()==0
    assert request.get(args.base_url+'/api/v1/feature-data/catalog/claims',headers=fixture['headers']['admin']).status==403
    assert request.post(base+'/claims.list/grant',headers=fixture['headers']['root']).status==201
    page.get_by_role('button',name='تحديث',exact=True).click();expect(page.locator('#sidebar a[href="/institution/claims"]')).to_be_visible()
    page.locator('#sidebar a[href="/institution/claims"]').click()
    expect(page.locator('main')).not_to_contain_text('وصول غير مصرح')
    assert request.get(args.base_url+'/api/v1/feature-data/catalog/claims',headers=fixture['headers']['admin']).status==200
    assert request.post(base+'/claims.list/revoke',headers=fixture['headers']['root'],data={'reason':'Synthetic revocation'}).status==200
    assert request.get(args.base_url+'/api/v1/feature-data/catalog/claims',headers=fixture['headers']['admin']).status==403
    page.get_by_role('button',name='تحديث',exact=True).click();expect(page.locator('#sidebar')).to_contain_text('لا ميزات مفعّلة')
    assert page.locator('#sidebar a[href="/institution/claims"]').count()==0
    page.screenshot(path=str(out/'no-enabled-features-ar.png'),full_page=True)
    assert page.evaluate('localStorage.length===0&&sessionStorage.length===0')
    checks=['default-deny empty navigation','real grant shows authorized route','temporal RBAC read bridge works',
        'revocation blocks direct API and refresh removes route','no sensitive browser storage']
    browser.close()
assert not errors,errors
result={'checks':checks,'page_errors':errors,'synthetic':True,'actual_http_and_postgresql':True}
(out/'navigation-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
