"""Executable Chromium E2E / accessibility suite; synthetic sources are explicit.

Run against an application started with MCIAS_ENABLE_UI_DEMO=true in development.
Production APIs are never mutated by this script. Mocked contract tests supplement
real API authorization tests in tests/test_enterprise_workspace.py.
"""
import argparse, json, os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8000');parser.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'));parser.add_argument('--output',default='.e2e-output');args=parser.parse_args()
OUTPUT=ROOT/args.output;OUTPUT.mkdir(parents=True,exist_ok=True)
routes=json.loads((ROOT/'mcias/web_workspace/routes.json').read_text())
fixture=json.loads((ROOT/'mcias/web_workspace/demo.json').read_text())
axe=(ROOT/'node_modules/axe-core/axe.min.js').read_text()
checks=[];errors=[];violations=[]

def navigate(page,path):
    page.evaluate('(path)=>{history.pushState({},"",path);window.dispatchEvent(new PopStateEvent("popstate"));}',path)
    expect(page.locator('main h1')).to_be_visible()
    page.wait_for_timeout(100)

def accessibility(page,name):
    page.evaluate(axe)
    result=page.evaluate('async()=>await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}})')
    bad=[{'screen':name,'id':v['id'],'impact':v['impact'],'nodes':[n['target'] for n in v['nodes']]} for v in result['violations']]
    violations.extend(bad)

def no_overflow(page,name):
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'),name+' has global horizontal overflow'

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'] if args.chromium else [])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.on('pageerror',lambda error: errors.append(str(error)))
    page.goto(args.base_url+'/institution/dashboard?demo=1')
    expect(page.locator('.kpi').first).to_be_visible();expect(page.locator('.banner.demo')).to_contain_text('عرض اصطناعي')
    assert page.locator('.kpi-value').all_text_contents()==['12000.00','8100.00','900.00','3']
    checks.append('evidence-backed dashboard values and explicit synthetic banner')
    accessibility(page,'institution-ar-light');no_overflow(page,'desktop Arabic')
    page.screenshot(path=str(OUTPUT/'institution-ar-light.png'),full_page=True)
    # Every specified route renders an intentional state, including dynamic records.
    for route in routes:
        path=route['path'].replace(':id',{'claim-detail':'SYN-demo-claim-1','user-detail':'SYN-synthetic-admin','eligibility':'demo-beneficiary','provider-detail':'SYN-PROVIDER'}.get(route['kind'],'demo-record'))
        navigate(page,path+'?demo=1')
        expect(page.locator('main h1')).to_have_text(route['ar'])
        if route['kind']=='unavailable': expect(page.locator('main')).to_contain_text('قدرة غير متاحة')
        no_overflow(page,path)
        if route['kind'] in ['claims','documents','tasks']:accessibility(page,path+'-ar')
    checks.append(f'{len(routes)} routes and dynamic record states')
    navigate(page,'/admin/dashboard?demo=1');accessibility(page,'admin-ar-light');page.screenshot(path=str(OUTPUT/'admin-ar-light.png'),full_page=True)
    page.get_by_role('button',name='EN',exact=True).click();expect(page.locator('html')).to_have_attribute('dir','ltr')
    expect(page.locator('h1')).to_have_text('Platform overview');accessibility(page,'admin-en-light');no_overflow(page,'desktop English')
    page.get_by_role('button',name='Theme',exact=True).click();expect(page.locator('html')).to_have_attribute('data-theme','dark')
    accessibility(page,'admin-en-dark');page.screenshot(path=str(OUTPUT/'admin-en-dark.png'),full_page=True)
    navigate(page,'/institution/dashboard?demo=1');accessibility(page,'institution-en-dark');page.screenshot(path=str(OUTPUT/'institution-en-dark.png'),full_page=True)
    checks.append('Arabic RTL, English LTR, light and dark accessibility')
    page.set_viewport_size({'width':768,'height':1024});no_overflow(page,'tablet');page.screenshot(path=str(OUTPUT/'institution-tablet.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844});no_overflow(page,'mobile English');accessibility(page,'institution-mobile-dark')
    page.get_by_role('button',name='Menu',exact=True).click();expect(page.locator('.shell')).to_have_class('shell nav-open')
    expect(page.get_by_role('button',name='Close menu',exact=True)).to_be_focused()
    page.keyboard.press('Escape');expect(page.locator('.shell')).to_have_class('shell');expect(page.locator('#sidebar')).to_have_attribute('inert','')
    page.get_by_role('button',name='عربي',exact=True).click();expect(page.locator('html')).to_have_attribute('dir','rtl');no_overflow(page,'mobile Arabic');accessibility(page,'institution-mobile-ar-dark')
    page.screenshot(path=str(OUTPUT/'institution-mobile-ar-dark.png'),full_page=True)
    checks.append('tablet/mobile layouts, drawer focus, escape and inert navigation')
    # Keyboard-operated source, table filters and evidence dialog.
    page.set_viewport_size({'width':1440,'height':1000});navigate(page,'/institution/claims?demo=1');expect(page.locator('tbody tr')).to_have_count(12)
    page.get_by_label('تصفية هذه الصفحة',exact=True).fill('SYN-001');expect(page.locator('tbody tr')).to_have_count(1)
    checks.append('claim table filtering and drill-down')
    navigate(page,'/institution/financial-audit?demo=1');page.get_by_role('button',name='عرض الدليل',exact=True).click();expect(page.locator('#drawer')).to_be_visible();expect(page.locator('#drawer')).to_contain_text('1000.00');expect(page.locator('#drawer')).to_contain_text('900.00');expect(page.locator('#drawer .finding')).to_have_count(8)
    accessibility(page,'audit-evidence-dialog');page.screenshot(path=str(OUTPUT/'audit-evidence.png'),full_page=True)
    page.keyboard.press('Escape');expect(page.locator('#drawer')).not_to_be_visible();checks.append('eight audit findings, backend decimal values and accessible evidence dialog')
    page.evaluate('()=>{window.confirmResult=null;import("/workspace-assets/ui.js").then(ui=>ui.confirm("Synthetic test confirmation").then(result=>window.confirmResult=result));}')
    expect(page.locator('#confirmation')).to_be_visible();page.get_by_role('button',name='تأكيد الإجراء',exact=True).click();page.wait_for_function('()=>window.confirmResult===true')
    page.evaluate('()=>{window.confirmResult=null;import("/workspace-assets/ui.js").then(ui=>ui.confirm("Synthetic cancel confirmation").then(result=>window.confirmResult=result));}')
    expect(page.locator('#confirmation')).to_be_visible();page.keyboard.press('Escape');page.wait_for_function('()=>window.confirmResult===false');checks.append('confirmation result resets; Escape never reuses a prior approval')
    navigate(page,'/admin/analysis-tasks?demo=1');assert page.locator('button[type=submit]').is_disabled();checks.append('synthetic mode blocks consequential actions')
    # Real frontend login/API-client integration against controlled HTTP contracts.
    live=browser.new_page(viewport={'width':1440,'height':1000});live.on('pageerror',lambda error:errors.append(str(error)))
    requests=[];user=json.loads(json.dumps(fixture['context']));user['roles']=['reader'];user['permissions']=['profile.read','claims.read','reports.read','reports.details.read'];from datetime import datetime,timedelta,timezone
    user['expires_at']=(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat()
    def fulfill(route):
        request=route.request;path=request.url.split(args.base_url)[-1];requests.append({'path':path,'method':request.method,'authorization':request.headers.get('authorization')})
        if path=='/api/v1/auth/login':route.fulfill(json={'access_token':'synthetic-browser-session','expires_in':1800});return
        if path=='/api/v1/workspace/context':route.fulfill(json=user);return
        if path.startswith('/api/v1/report-explorer/snapshots'):route.fulfill(json={'items':fixture['reports'],'has_more':False});return
        if path.startswith('/api/v1/workspace/catalog/claims'):
            claims=json.loads(json.dumps(fixture['catalog']['claims']));claims[0]['claim_reference']='<img src=x onerror=alert(1)>'
            route.fulfill(json={'items':claims,'has_more':False});return
        if path=='/api/v1/auth/logout':route.fulfill(status=204);return
        route.fulfill(status=403,json={'detail':'forbidden'})
    live.route('**/api/v1/**',fulfill);live.goto(args.base_url+'/login')
    live.get_by_label('اسم المستخدم',exact=True).fill('synthetic');live.get_by_label('كلمة المرور',exact=True).fill('synthetic_password');live.get_by_role('button',name='تسجيل الدخول بأمان',exact=True).click();expect(live.locator('.kpi').first).to_be_visible()
    assert requests[1]['authorization']=='Bearer synthetic-browser-session';assert not live.locator('.banner.demo').count();checks.append('login, memory-only bearer session, authorized report integration')
    navigate(live,'/institution/claims');expect(live.locator('tbody tr')).to_have_count(12);expect(live.locator('tbody')).to_contain_text('<img src=x onerror=alert(1)>');assert live.locator('tbody img').count()==0
    assert live.evaluate('localStorage.length===0&&sessionStorage.length===0');checks.append('XSS-safe server text and no sensitive browser storage')
    navigate(live,'/admin/dashboard');expect(live.locator('main')).to_contain_text('وصول غير مصرح');checks.append('administration role guard')
    navigate(live,'/institution/evidence');expect(live.locator('main')).to_contain_text('وصول غير مصرح');assert not any('/catalog/documents' in r['path'] for r in requests);checks.append('permission-aware reads prevented before request')
    navigate(live,'/institution/claims');live.unroute('**/api/v1/**');live.route('**/api/v1/**',lambda route:route.fulfill(status=401,json={'detail':'expired'}));live.get_by_role('button',name='تحديث',exact=True).click();expect(live.locator('#login-form')).to_be_visible();assert live.locator('tbody').count()==0;assert live.locator('#drawer').text_content()=='';checks.append('expired session removes all protected content')
    accessibility(live,'login-ar');live.screenshot(path=str(OUTPUT/'login-ar.png'),full_page=True)
    browser.close()
result={'checks':checks,'route_count':len(routes),'page_errors':errors,'accessibility_violations':violations,'synthetic_data':True}
(OUTPUT/'browser-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
assert not errors, errors
assert not violations, violations
