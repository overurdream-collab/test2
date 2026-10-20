"""Actual Chromium -> FastAPI -> PostgreSQL session/read/logout E2E test."""
import argparse,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8001');p.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'));args=p.parse_args()
f=json.loads((ROOT/'.e2e-output/live-fixture.json').read_text());checks=[]
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


# W1 focused role matrix: actual FastAPI sessions, never mocked API responses.
# The deterministic synthetic seed above is required; no production identities are used.
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from mcias.models import Organization, User, Role, UserRole, Permission, RolePermission, MFAFactor
from mcias.security import hash_password
from mcias.mfa import generate_totp
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import time
engine=create_engine(os.environ['MCIAS_E2E_DATABASE_URL'])
secret=b'W1-only-synthetic-MFA-secret-32-bytes'
password='synthetic_e2e_password_only'
with Session(engine) as db:
 org=db.scalar(select(Organization).where(Organization.id==f['organization_id']))
 assert org is not None
 foreign=db.scalar(select(Organization).where(Organization.id!=org.id))
 assert foreign is not None
 for role_code in ('super_admin','admin'):
  role=db.scalar(select(Role).where(Role.code==role_code))
  if role is None:
   role=Role(code=role_code);db.add(role);db.flush()
  username='SYN-W1-'+role_code
  actor=db.scalar(select(User).where(User.username==username))
  if actor is None:
   actor=User(organization_id=org.id,username=username,password_hash=hash_password(password))
   db.add(actor);db.flush()
   db.add(UserRole(user_id=actor.id,role_id=role.id))
  for code in ('profile.read','claims.read','reports.read','users.read'):
   perm=db.scalar(select(Permission).where(Permission.code==code))
   if perm is None:
    perm=Permission(code=code);db.add(perm);db.flush()
   if db.get(RolePermission,(role.id,perm.id)) is None:
    db.add(RolePermission(role_id=role.id,permission_id=perm.id))
  if role_code=='super_admin' and db.get(MFAFactor,actor.id) is None:
   nonce=os.urandom(12)
   ciphertext=AESGCM(bytes.fromhex(os.environ['MCIAS_MFA_ENCRYPTION_KEY'])).encrypt(nonce,secret,actor.id.encode())
   db.add(MFAFactor(user_id=actor.id,encrypted_secret=nonce+ciphertext,enabled=True,last_accepted_counter=-1))
 foreign_user=db.scalar(select(User).where(User.username=='SYN-W1-FOREIGN'))
 if foreign_user is None:
  foreign_user=User(organization_id=foreign.id,username='SYN-W1-FOREIGN',password_hash=hash_password(password))
  db.add(foreign_user);db.flush()
 foreign_id=foreign_user.id
 db.commit()
engine.dispose()

matrix=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'] if args.chromium else [])
 for role in ('super_admin','admin','user'):
  page=browser.new_page(viewport={'width':1440,'height':900})
  tokens=[]
  page.on('response',lambda response: tokens.append(response.json()['access_token']) if response.url.endswith('/api/v1/auth/login') and response.status==200 else None)
  page.goto(args.base_url+'/login')
  page.get_by_label('اسم المستخدم',exact=True).fill(f['username'] if role=='user' else 'SYN-W1-'+role)
  page.get_by_label('كلمة المرور',exact=True).fill(password)
  if role=='super_admin':
   page.get_by_label('رمز التحقق (إلزامي للإدارة)',exact=True).fill(generate_totp(secret,int(time.time())//30))
  page.get_by_role('button',name='تسجيل الدخول بأمان',exact=True).click()
  expect(page.locator('.kpi').first).to_be_visible(timeout=15000)
  assert len(tokens)==1,role+' real backend token absent'
  headers={'Authorization':'Bearer '+tokens[0]}
  context=page.request.get(args.base_url+'/api/v1/workspace/context',headers=headers)
  assert context.status==200 and context.json()['organization']['id']==org.id
  assert ('super_admin' in context.json()['roles'])==(role=='super_admin')
  expect(page.locator('#sidebar nav')).to_be_visible()
  page.get_by_role('button',name='EN',exact=True).click()
  expect(page.locator('html')).to_have_attribute('dir','ltr')
  page.get_by_role('button',name='عربي',exact=True).click()
  expect(page.locator('html')).to_have_attribute('dir','rtl')
  page.set_viewport_size({'width':390,'height':844})
  page.get_by_role('button',name='القائمة',exact=True).click()
  expect(page.locator('.shell')).to_have_class('shell nav-open')
  page.get_by_role('button',name='إغلاق القائمة',exact=True).click()
  page.set_viewport_size({'width':1440,'height':900})
  page.evaluate('()=>{history.pushState({},"","/admin/users");dispatchEvent(new PopStateEvent("popstate"));}')
  api=page.request.get(args.base_url+'/api/v1/workspace/catalog/users',headers=headers)
  detail=page.request.get(args.base_url+'/api/v1/workspace/users/'+foreign_id,headers=headers)
  if role=='super_admin':
   assert api.status==200 and api.json()['scope']=='current_organization'
   items=api.json()['items']
   assert items and all(set(x).issubset({'id','username','active','created_at'}) for x in items)
   assert all(x['id']!=foreign_id for x in items)
   assert detail.status==404
   expect(page.locator('.staff-card').first).to_be_visible()
   assert page.locator('.staff-card').count()==len(items)
   assert page.locator('main button').filter(has_text='حذف').count()==0
   assert page.locator('main button').filter(has_text='تعديل').count()==0
   # The API exposes boolean active, never a status string.
   assert all(isinstance(x['active'],bool) for x in items)
   page.locator('#w1-users-status').select_option('active')
   assert page.locator('.staff-card').count()==sum(x['active'] for x in items)
   page.locator('#w1-users-status').select_option('disabled')
   assert page.locator('.staff-card').count()==sum(not x['active'] for x in items)
  else:
   assert api.status==403 and detail.status==403,(role,api.status,detail.status)
   expect(page.locator('main')).to_contain_text('وصول غير مصرح')
   assert page.locator('.staff-card').count()==0
  page.screenshot(path=str(ROOT/'.e2e-output'/('w1-'+role+'-users.png')),full_page=True)
  matrix.append({'role':role,'real_session':True,'dashboard_navigation_ar_en_desktop_mobile':'PASS',
                 'users_api':api.status,'foreign_user_detail':detail.status,
                 'users_ui':'PASS','tenant_isolation':'PASS'})
  page.close()
 browser.close()
(ROOT/'.e2e-output'/'w1-role-matrix.json').write_text(json.dumps({'matrix':matrix,'synthetic':True,'security_skipped':0},indent=2)+'\n')
print(json.dumps({'w1_role_matrix':matrix,'security_skipped':0},indent=2))
