"""Workspace read-model privacy, tenant isolation, pagination and asset delivery."""
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from mcias.app import app, get_db
from mcias.models import Base, Organization, User, Permission, Role, RolePermission, UserRole, SessionToken
from mcias.models_claims import ClaimBatch, ClaimEntry
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord
from mcias.models import SourceFile
from mcias.security import hash_password

ROOT=Path(__file__).resolve().parents[1]
ROUTES=json.loads((ROOT/'mcias/web_workspace/routes.json').read_text())

@pytest.fixture
def client():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Organization(id='org-a',name='Synthetic A'),Organization(id='org-b',name='Synthetic B')]);db.flush()
        db.add_all([User(id='actor',organization_id='org-a',username='synthetic',password_hash=hash_password('synthetic_password')),User(id='other',organization_id='org-b',username='foreign',password_hash='not returned')]);db.flush()
        db.add(Role(id='read-role',code='reader'));db.add(UserRole(user_id='actor',role_id='read-role'))
        for code in ['profile.read','claims.read','ingestion.read']:
            db.add(Permission(id=code,code=code));db.flush();db.add(RolePermission(role_id='read-role',permission_id=code))
        db.add(SessionToken(user_id='actor',token_hash=hashlib.sha256(b'test-session').hexdigest(),expires_at=datetime.now(timezone.utc)+timedelta(minutes=15)))
        db.add_all([SourceFile(id='s-a',sha256='a'*64,original_filename='PRIVATE-NAME.csv',storage_key='PRIVATE-KEY'),SourceFile(id='s-b',sha256='b'*64,original_filename='FOREIGN.csv',storage_key='FOREIGN-KEY')]);db.flush()
        for suffix in ['a','b']:
            db.add(IngestionDocument(id='doc-'+suffix,organization_id='org-'+suffix,source_id='s-'+suffix,sha256=suffix*64,filename='PRIVATE-NAME.csv',status='extracted'));db.flush()
            db.add(IngestionJob(id='job-'+suffix,document_id='doc-'+suffix,organization_id='org-'+suffix,status='extracted'));db.flush()
            db.add(ExtractedSourceRecord(id='record-'+suffix,job_id='job-'+suffix,locator={'row':1},values={'diagnosis':'NEVER-RETURN'}));db.flush()
            db.add(ClaimBatch(id='batch-'+suffix,organization_id='org-'+suffix,ingestion_document_id='doc-'+suffix,created_by='actor' if suffix=='a' else 'other',status='imported',source_sha256=suffix*64,record_count=1,imported_count=1));db.flush()
            db.add(ClaimEntry(id='claim-'+suffix,organization_id='org-'+suffix,batch_id='batch-'+suffix,extracted_record_id='record-'+suffix,source_locator={'row':1},source_values={'diagnosis':'NEVER-RETURN'},claim_reference='SYN-'+suffix,beneficiary_token='PRIVATE-TOKEN',provider_code='PRIVATE-PROVIDER',service_code='PRIVATE-SERVICE',service_date=datetime.now().date(),claimed_amount='0.0100',currency='LYD'))
        db.commit()
    def dependency():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db]=dependency
    with TestClient(app) as test:
        yield test,engine
    app.dependency_overrides.pop(get_db,None)
    engine.dispose()

HEADERS={'Authorization':'Bearer test-session'}

def test_context_effective_permissions_no_secrets(client):
    c,_=client
    r=c.get('/api/v1/workspace/context',headers=HEADERS)
    assert r.status_code==200
    data=r.json();assert data['organization']=={'id':'org-a','name':'Synthetic A'}
    assert data['permissions']==['claims.read','ingestion.read','profile.read']
    assert data['institutionally_accepted'] is False and data['tenant_switching'] is False
    assert 'password' not in r.text and 'token_hash' not in r.text
    assert r.headers['cache-control']=='no-store'

def test_catalog_is_tenant_scoped_and_excludes_raw_fields(client):
    c,_=client
    r=c.get('/api/v1/workspace/catalog/claims',headers=HEADERS)
    assert r.status_code==200 and len(r.json()['items'])==1
    item=r.json()['items'][0];assert item['id']=='claim-a'
    assert item['claimed_amount']=='0.0100'
    for private in ['NEVER-RETURN','PRIVATE-TOKEN','PRIVATE-PROVIDER','PRIVATE-SERVICE','FOREIGN','source_values','beneficiary_token']:
        assert private not in r.text
    document=c.get('/api/v1/workspace/catalog/documents',headers=HEADERS)
    assert document.status_code==200 and 'PRIVATE-NAME' not in document.text and 'storage_key' not in document.text
    assert c.get('/api/v1/workspace/claims/claim-b',headers=HEADERS).status_code==404
    assert c.get('/api/v1/workspace/claims/claim-a',headers=HEADERS).json()['claimed_amount']=='0.0100'

def test_default_deny_and_bounded_query(client):
    c,_=client
    assert c.get('/api/v1/workspace/catalog/claims').status_code==401
    assert c.get('/api/v1/workspace/catalog/users',headers=HEADERS).status_code==403
    assert c.get('/api/v1/workspace/catalog/contracts',headers=HEADERS).status_code==403
    assert c.get('/api/v1/workspace/catalog/arbitrary_sql',headers=HEADERS).status_code==404
    assert c.get('/api/v1/workspace/catalog/claims?limit=101',headers=HEADERS).status_code==422
    assert c.get('/api/v1/workspace/catalog/claims?offset=-1',headers=HEADERS).status_code==422
    assert c.get('/api/v1/workspace/catalog/claims?offset=1',headers=HEADERS).json()['items']==[]

def test_admin_user_records_need_role_and_permission_and_same_tenant(client):
    c,engine=client
    with Session(engine) as db:
        db.add(Permission(id='users.read',code='users.read'));db.add(RolePermission(role_id='read-role',permission_id='users.read'));db.commit()
    assert c.get('/api/v1/workspace/catalog/users',headers=HEADERS).status_code==403
    with Session(engine) as db:
        db.add(Role(id='admin',code='super_admin'));db.add(UserRole(user_id='actor',role_id='admin'));db.commit()
    r=c.get('/api/v1/workspace/catalog/users',headers=HEADERS)
    assert r.status_code==200 and len(r.json()['items'])==1
    assert 'password_hash' not in r.text
    assert c.get('/api/v1/workspace/users/other',headers=HEADERS).status_code==404

def test_expired_and_revoked_sessions_are_denied(client):
    c,engine=client
    with Session(engine) as db:
        token=db.query(SessionToken).first();token.revoked_at=datetime.now(timezone.utc);db.commit()
    assert c.get('/api/v1/workspace/context',headers=HEADERS).status_code==401

@pytest.mark.parametrize('route',[r['path'].replace(':id','synthetic-record') for r in ROUTES]+['/login','/mfa','/forgot-password'])
def test_every_declared_route_serves_public_safe_shell(route):
    r=TestClient(app).get(route)
    assert r.status_code==200 and 'lang="ar" dir="rtl"' in r.text
    assert '/workspace-assets/app.js' in r.text
    assert r.headers['cache-control']=='no-store'
    assert "script-src 'self'" in r.headers['content-security-policy']
    assert '<script>' not in r.text and 'access_token' not in r.text

def test_static_asset_whitelist_and_csp():
    c=TestClient(app)
    for asset in ['app.js','ui.js','api.js','views.js','workspace.css','routes.json','icons/audit.svg','fonts/plex-ar-400.woff2']:
        r=c.get('/workspace-assets/'+asset)
        assert r.status_code==200 and r.headers['cache-control']=='no-store'
        assert "style-src 'self'" in r.headers['content-security-policy']
    assert c.get('/workspace-assets/index.html').status_code==404
    assert c.get('/workspace-assets/../../models.py').status_code==404
    assert c.get('/workspace-assets/nonexistent.js').status_code==404

def test_synthetic_preview_is_explicit_and_never_production(monkeypatch):
    monkeypatch.setenv('MCIAS_DATABASE_URL','sqlite://')
    monkeypatch.setenv('MCIAS_BOOTSTRAP_TOKEN','synthetic_test_only')
    monkeypatch.setenv('MCIAS_ENABLE_UI_DEMO','true')
    monkeypatch.setenv('MCIAS_ENVIRONMENT','production')
    c=TestClient(app);assert c.get('/api/v1/workspace/demo-availability').json()=={'enabled':False}
    monkeypatch.setenv('MCIAS_ENVIRONMENT','development')
    assert c.get('/api/v1/workspace/demo-availability').json()=={'enabled':True}
    monkeypatch.delenv('MCIAS_ENABLE_UI_DEMO')
    assert c.get('/api/v1/workspace/demo-availability').json()=={'enabled':False}
