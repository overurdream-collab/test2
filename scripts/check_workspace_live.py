"""Actual Chromium -> FastAPI -> PostgreSQL session/read/logout E2E test."""
import argparse,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8001');p.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'));args=p.parse_args()
f=json.loads((ROOT/'.e2e-output/live-fixture.json').read_text());checks=[]
# This fixture authorization is explicit test setup, never runtime/default Seed.
# Reuse the verified synthetic operator created by check_integrated_workflow.
from sqlalchemy import create_engine,select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from mcias.models import User,Role,UserRole,MFAFactor
from mcias.services import feature_service as features
fixture_url=os.environ['MCIAS_E2E_DATABASE_URL']
if os.getenv('MCIAS_ENVIRONMENT')!='development' or not make_url(fixture_url).database.endswith('_e2e'):
 raise ValueError('dedicated synthetic browser database required')
with Session(create_engine(fixture_url)) as db:
 reader=db.scalar(select(User).where(User.username==f['username']))
 operator=db.scalar(select(User).join(UserRole,UserRole.user_id==User.id).join(Role,Role.id==UserRole.role_id)
   .join(MFAFactor,MFAFactor.user_id==User.id).where(User.username.like('workflow-operator-%'),Role.code=='super_admin',MFAFactor.enabled.is_(True)).limit(1))
 if not operator:raise ValueError('run the integrated synthetic workflow first')
 for code in ('dashboard.summary','claims.list','reports.list'):
  if not features.check_feature(db,reader.organization_id,code):features.grant_feature(db,reader.organization_id,code,operator.id)
 db.commit()
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'] if args.chromium else [])
 page=b.new_page(viewport={'width':1440,'height':1000});errors=[];requests=[]
 page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
 page.goto(args.base_url+'/login');page.get_by_label('اسم المستخدم',exact=True).fill(f['username']);page.get_by_label('كلمة المرور',exact=True).fill(f['password']);page.get_by_role('button',name='تسجيل الدخول بأمان',exact=True).click();expect(page.locator('.kpi').first).to_be_visible()
 assert page.locator('.kpi-value').all_text_contents()==['12000.0000','0','0','12'];assert not page.locator('.banner.demo').count();checks.append('real login/session and frozen PostgreSQL report totals')
 page.evaluate('()=>{history.pushState({},"","/institution/claims");dispatchEvent(new PopStateEvent("popstate"));}');expect(page.locator('tbody tr')).to_have_count(12);assert 'SYNTHETIC_PRIVATE_FIELD_NOT_DISCLOSED' not in page.locator('body').text_content();checks.append('tenant-scoped real claim catalog excludes raw medical fields')
 page.get_by_role('button',name='عرض الدليل',exact=True).first.click();expect(page.locator('h1')).to_have_text('تفاصيل المطالبة');expect(page.locator('main')).to_contain_text('1000.0000');checks.append('real protected claim detail drill-down')
 page.evaluate('()=>{history.pushState({},"","/admin/dashboard");dispatchEvent(new PopStateEvent("popstate"));}');expect(page.locator('main')).to_contain_text('وصول غير مصرح');checks.append('real reader identity cannot enter administrative interface')
 page.get_by_role('button',name='خروج',exact=True).click();expect(page.locator('#login-form')).to_be_visible();assert page.locator('tbody').count()==0;assert page.evaluate('localStorage.length===0&&sessionStorage.length===0');checks.append('real backend logout revokes session and clears protected DOM')
 assert not errors,errors;assert all(url.startswith(args.base_url) for url in requests),'Unexpected external browser request'
 checks.append('zero external browser requests or JavaScript errors')
 b.close()
result={'checks':checks,'actual_http_and_postgresql':True,'synthetic_data':True,'errors':errors}
(ROOT/'.e2e-output/live-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
