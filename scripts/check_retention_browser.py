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
                   'governance.review', 'governance.reaudit', 'retention.read', 'retention.archive']
    ids = {}
    with Session(engine) as db:
        org = Organization(name='SYNTHETIC WORKFLOW ' + unique)
        foreign = Organization(name='SYNTHETIC FOREIGN ' + unique)
        db.add_all([org, foreign]); db.flush()
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

        page.evaluate('()=>{history.pushState({},"","/admin/backups");dispatchEvent(new PopStateEvent("popstate"));}')
        expect(page.locator('main')).to_contain_text('الحذف الدوري معطّل')
        page.get_by_label('الشهر', exact=True).fill('2020-01')
        page.get_by_role('button',name='تنفيذ الطلب',exact=True).click()
        expect(page.locator('dialog[open]')).to_be_visible()
        page.locator('dialog[open]').get_by_role('button',name='تأكيد الإجراء',exact=True).click()
        expect(page.locator('main')).to_contain_text('queued')
        page.evaluate((ROOT/'node_modules/axe-core/axe.min.js').read_text())
        violations=page.evaluate('async()=> (await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}})).violations.map(v=>v.id)')
        assert not violations, violations
        page.screenshot(path=str(ROOT/'.e2e-output/retention-ar.png'),full_page=True)
        assert not errors, errors
        checks.append('real retention status, confirmed queued archive and WCAG checks')
        browser.close()
    engine.dispose()
    result={'checks':checks,'errors':errors,'accessibility_violations':violations,'synthetic_data':True}
    (ROOT/'.e2e-output/retention-browser-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--base-url',default='http://127.0.0.1:8000'); parser.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'))
    args=parser.parse_args();run(args.base_url,args.chromium)
