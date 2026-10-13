"""Explicit synthetic laptop bootstrap, never institutional provisioning."""
from __future__ import annotations
import argparse
import base64
import json
import os
import re
import secrets
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from mcias.seed.config import SeedConfig
from mcias.seed.loader import load, identifier
from mcias.models import User, Role, Permission, UserRole, RolePermission, MFAFactor, AuditLog
from mcias.security import hash_password, verify_password

ADMIN_PERMISSIONS = (
 'profile.read','users.read','claims.read','claims.import','ingestion.read','ingestion.upload',
 'reference.read','reference.write','reference.approve','rules.read','rules.activate','rules.exclusions.edit',
 'reports.read','reports.create','reports.export','reports.details.read','reports.beneficiary.read',
 'governance.propose','governance.review','governance.reaudit',
 'intelligence.read','intelligence.run','intelligence.review','intelligence.studio.read',
 'intelligence.studio.manage','intelligence.studio.test','retention.read',
)
REVIEWER_PERMISSIONS = ('profile.read','claims.read','reports.read','reports.details.read',
 'reference.read','reference.approve','governance.review','governance.approve','governance.reaudit',
 'intelligence.read','intelligence.review','intelligence.studio.read','intelligence.studio.activate')
MUTABLE_TABLES = ('session_tokens','mfa_factors','login_attempts','api_rate_limit_buckets',
 'contract_versions','rule_versions','ingestion_documents','ingestion_jobs','ingestion_quarantine','claim_batches')


def guard(env):
    if env.get('MCIAS_LAPTOP_TEST_MODE') != 'synthetic_localhost' or env.get('MCIAS_ENVIRONMENT') != 'development':
        raise ValueError('explicit synthetic laptop mode required')
    url = make_url(env.get('MCIAS_DATABASE_URL',''))
    if url.drivername != 'postgresql+psycopg' or url.database != 'mcias_laptop_e2e' or url.username != 'laptop_runtime':
        raise ValueError('dedicated laptop PostgreSQL database required')
    for variable in ('MCIAS_MFA_ENCRYPTION_KEY','MCIAS_STORAGE_KEY'):
        if not re.fullmatch('[0-9a-fA-F]{64}',env.get(variable,'')) or int(env[variable],16)==0:
            raise ValueError('fresh valid local encryption keys required')
    return url


def private_json(path, payload):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError('private path must not be symbolic')
    temporary=path.with_suffix('.tmp')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(payload,stream,ensure_ascii=False,indent=2)
            stream.flush();os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def grant_runtime(engine, password):
    if not re.fullmatch('[0-9a-f]{64}',password):
        raise ValueError('invalid runtime credential format')
    # Only fixed identifiers and a validated hex password enter this utility DDL.
    with engine.begin() as connection:
        exists=connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname='laptop_runtime'")).scalar()
        if not exists:
            connection.exec_driver_sql("CREATE ROLE laptop_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '"+password+"'")
        connection.exec_driver_sql('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        connection.exec_driver_sql('GRANT CONNECT ON DATABASE mcias_laptop_e2e TO laptop_runtime')
        connection.exec_driver_sql('GRANT USAGE ON SCHEMA public TO laptop_runtime')
        connection.exec_driver_sql('GRANT SELECT ON ALL TABLES IN SCHEMA public TO laptop_runtime')
        import mcias.models_authorization  # reviewed grant inserts
        import mcias.models_g8  # register all intelligence insert grants
        import mcias.models_operations  # register limiter inserts before granting
        import mcias.models_audit_policy
        import mcias.models_reference
        from mcias.models import Base
        for table in sorted(Base.metadata.tables):
            # The mappings supply trusted table names; this is not caller SQL.
            if not re.fullmatch('[a-z][a-z0-9_]*',table):
                raise ValueError('unexpected mapped table name')
            connection.exec_driver_sql(f'GRANT INSERT ON {table} TO laptop_runtime')
        for table in MUTABLE_TABLES:
            connection.exec_driver_sql(f'GRANT UPDATE, DELETE ON {table} TO laptop_runtime')
        connection.exec_driver_sql('REVOKE UPDATE, DELETE ON audit_log FROM laptop_runtime')


def setup(env):
    runtime=guard(env)
    owner=make_url(env.get('MCIAS_E2E_DATABASE_URL',''))
    if owner.database!=runtime.database or owner.host!=runtime.host or owner.port!=runtime.port or owner.username!='laptop_owner':
        raise ValueError('dedicated administrative setup identity required')
    state=Path(env['MCIAS_LAPTOP_STATE_DIR'])/'laptop-credentials.json'
    if state.is_symlink(): raise ValueError('private state cannot be symbolic')
    # Restart must allow additional user-entered test claims. The seed loader's
    # exact-count receipt is only appropriate on first installation.
    saved=json.loads(state.read_text()) if state.exists() else None
    seed=saved or load(SeedConfig(owner.render_as_string(hide_password=False),'development'))
    engine=create_engine(owner,connect_args={'connect_timeout':3})
    try:
        grant_runtime(engine,env['MCIAS_LAPTOP_RUNTIME_PASSWORD'])
        with Session(engine) as db:
            db.execute(text('SELECT pg_advisory_xact_lock(31233667)'))
            if state.exists():
                saved=json.loads(state.read_text())
                for item in saved['accounts']:
                    actor=db.get(User,item['id'])
                    if not actor or actor.organization_id!=seed['organization_id'] or not verify_password(item['password'],actor.password_hash):
                        raise ValueError('private credentials do not match seeded accounts; do not overwrite keys/state')
                from mcias.seed.institution import ensure_admin
                updated = ensure_admin(db, seed['organization_id'], saved['accounts'], env, ADMIN_PERMISSIONS)
                from mcias.seed.authorization import approve_synthetic
                approve_synthetic(db,seed['organization_id'],'development')
                if updated: private_json(state, saved)
                db.commit()
                return {'status':'READY','synthetic':True,'reused':True}
            if db.get(User,identifier('laptop-admin')):
                raise ValueError('account exists without private state; operator recovery required')
            accounts=[]
            for name,permissions in [('admin',ADMIN_PERMISSIONS),('reviewer',REVIEWER_PERMISSIONS)]:
                password=secrets.token_urlsafe(24)
                actor=User(id=identifier('laptop-'+name),organization_id=seed['organization_id'],
                    username='SYN-laptop-'+name,password_hash=hash_password(password))
                role=Role(id=identifier('laptop-'+name+'-role'),code='SYN-laptop-'+name)
                db.add_all([actor,role]);db.flush()
                db.add(UserRole(user_id=actor.id,role_id=role.id))
                for code in permissions:
                    permission=db.scalar(select(Permission).where(Permission.code==code))
                    if permission is None:
                        permission=Permission(code=code);db.add(permission);db.flush()
                    db.add(RolePermission(role_id=role.id,permission_id=permission.id))
                secret=secrets.token_bytes(20);nonce=secrets.token_bytes(12)
                encrypted=AESGCM(bytes.fromhex(env['MCIAS_MFA_ENCRYPTION_KEY'])).encrypt(nonce,secret,actor.id.encode())
                db.add(MFAFactor(user_id=actor.id,encrypted_secret=nonce+encrypted,enabled=True))
                if name=='admin':
                    super_admin=db.scalar(select(Role).where(Role.code=='super_admin'))
                    if super_admin is None:
                        super_admin=Role(code='super_admin');db.add(super_admin);db.flush()
                    db.add(UserRole(user_id=actor.id,role_id=super_admin.id))
                accounts.append({'id':actor.id,'username':actor.username,'password':password,
                    'totp_secret_base32':base64.b32encode(secret).decode().rstrip('=')})
            db.add(AuditLog(actor_id=accounts[0]['id'],action='synthetic_laptop_bootstrap',resource_type='test_environment',details={'synthetic':True}))
            db.flush()
            from mcias.seed.institution import ensure_admin
            ensure_admin(db, seed['organization_id'], accounts, env, ADMIN_PERMISSIONS)
            from mcias.seed.authorization import approve_synthetic
            approve_synthetic(db,seed['organization_id'],'development')
            private_json(state,{'synthetic':True,'organization_id':seed['organization_id'],'accounts':accounts})
            db.commit()
        return {'status':'READY','synthetic':True,'reused':False}
    finally: engine.dispose()


def check(env, *, verify_mfa=False, verify_inputs=False):
    guard(env)
    from mcias.preflight_g9 import check_postgres_role
    controls=check_postgres_role(env['MCIAS_DATABASE_URL'])
    def request(path,payload=None,token=None):
        headers={'Content-Type':'application/json'}
        if token: headers['Authorization']='Bearer '+token
        data=payload if isinstance(payload,bytes) else None if payload is None else json.dumps(payload).encode()
        req=Request('http://127.0.0.1:8000'+path,data=data,headers=headers)
        with urlopen(req,timeout=5) as response:
            body=response.read(65536)
            return response.status, json.loads(body) if body else None
    for path,expected in [('/health/live','ok'),('/health/ready','ready')]:
        try: ok=request(path)[1]['status']==expected
        except Exception: ok=False
        controls.append({'control':path,'status':'PASS' if ok else 'BLOCKED'})
    try:
        token=request('/api/v1/auth/login',{'username':'SYN-workspace-reader','password':'synthetic_e2e_password_only'})[1]['access_token']
        context=request('/api/v1/workspace/context',token=token)[1]
        controls.append({'control':'reader_authentication','status':'PASS' if 'claims.read' in context['permissions'] else 'BLOCKED'})
        claims=request('/api/v1/workspace/catalog/claims?limit=5',token=token)[1]
        controls.append({'control':'seed_claims','status':'PASS' if claims.get('items') else 'BLOCKED'})
        try:
            request('/api/v1/workspace/catalog/users',token=token)
            denied=False
        except HTTPError as exc: denied=exc.code==403
        controls.append({'control':'reader_admin_denied','status':'PASS' if denied else 'BLOCKED'})
        receipt=Path(env['MCIAS_LAPTOP_STATE_DIR'])/'laptop-smoke.json'
        if receipt.exists():
            if receipt.is_symlink(): raise ValueError('symbolic smoke receipt')
            saved=json.loads(receipt.read_text())
            detail=request('/api/v1/workspace/claims/'+saved['claim_id'],token=token)[1]
            persisted=detail['claim_reference']==saved['claim_reference'] and detail['claimed_amount']==saved['claimed_amount']
            controls.append({'control':'entered_claim_persistence','status':'PASS' if persisted else 'BLOCKED'})
        request('/api/v1/auth/logout',{},token)
    except Exception:
        controls.append({'control':'authenticated_smoke','status':'BLOCKED'})
    if verify_mfa:
        # Opt-in fresh-install integration check; passwords/TOTP never leave
        # this container or appear in command arguments/results.
        from mcias.mfa import generate_totp
        path=Path(env['MCIAS_LAPTOP_STATE_DIR'])/'laptop-credentials.json'
        if path.is_symlink(): raise ValueError('symbolic private state')
        accounts=json.loads(path.read_text())['accounts']
        for account in accounts:
            name={'SYN-laptop-admin':'admin', 'SYN-laptop-reviewer':'reviewer',
                  'SYN-laptop-institution-admin':'institution_admin'}[account['username']]
            try:
                payload={key:account[key] for key in ('username','password')}
                try:
                    request('/api/v1/auth/login',payload)
                    missing_denied=False
                except HTTPError as exc: missing_denied=exc.code==401
                encoded=account['totp_secret_base32']
                secret=base64.b32decode(encoded+'='*((-len(encoded))%8))
                payload['totp_code']=generate_totp(secret,int(time.time())//30)
                token=request('/api/v1/auth/login',payload)[1]['access_token']
                context=request('/api/v1/workspace/context',token=token)[1]
                permissions=set(context['permissions'])
                if name=='admin': separated='governance.approve' not in permissions and 'super_admin' in context['roles']
                elif name=='reviewer': separated='governance.propose' not in permissions and 'governance.approve' in permissions
                else:
                    from mcias.services.authorization_service import FINANCIAL_APPROVALS
                    separated=context.get('institution_admin') and 'super_admin' not in context['roles'] and not FINANCIAL_APPROVALS.intersection(permissions)
                separated=separated and not any(p.startswith('medical_fields.') for p in permissions)
                try:
                    request('/api/v1/auth/login',payload)
                    replay_denied=False
                except HTTPError as exc: replay_denied=exc.code==401
                try:
                    request('/api/v1/workspace/catalog/users',token=token)
                    admin_access=name in ('admin','institution_admin')
                except HTTPError as exc: admin_access=name=='reviewer' and exc.code==403
                if name=='institution_admin':
                    overview=request('/api/v1/institution/overview',token=token)[1]
                    names=request('/api/v1/registry/beneficiaries.names/records',token=token)[1]
                    directory=request('/api/v1/institution/users',token=token)[1]
                    controls.append({'control':'institution_dashboard_and_inputs','status':'PASS' if
                        all(m['status']=='available' for m in overview['metrics'].values()) and isinstance(names['items'],list)
                        and any(u['id']==account['id'] for u in directory['items']) else 'BLOCKED'})
                if verify_inputs and name=='admin':
                    suffix=secrets.token_hex(6)
                    contract=request('/api/v1/reference/contracts',{'provider_code':'SYN-LAP-'+suffix,
                        'effective_from':'2026-01-01','effective_until':'2027-01-01'},token)[1]
                    tariff=request('/api/v1/reference/contracts/'+contract['id']+'/tariffs',
                        {'service_code':'SYN-SERVICE','amount':'100.00','currency':'LYD'},token)[1]
                    category=request('/api/v1/reference/categories',{'code':'SYN-LAP-'+suffix,'description':'Synthetic laptop test only'},token)[1]
                    request('/api/v1/reference/enrollments',{'beneficiary_token':'SYN-LAP-'+suffix,
                        'category_id':category['id'],'effective_from':'2026-01-01','effective_until':'2027-01-01'},token)
                    eligible=request('/api/v1/reference/eligibility/SYN-LAP-'+suffix+'?at=2026-10-01',token=token)[1]['eligible']
                    data=('claim_reference,beneficiary_token,provider_code,service_code,service_date,claimed_amount,currency\n'
                        f'SYN-LAP-{suffix},SYN-LAP-{suffix},SYN-LAP-{suffix},SYN-SERVICE,2026-10-01,100.00,LYD\n').encode()
                    upload=request('/api/v1/ingestion/uploads?filename=SYN-laptop.csv',data,token)[1]
                    batch=request('/api/v1/claims/batches/from-document/'+upload['document_id'],{},token)[1]
                    request('/api/v1/claims/batches/'+batch['id']+'/resume',{},token)
                    entries=request('/api/v1/claims/batches/'+batch['id']+'/entries',token=token)[1]['entries']
                    valid=contract['status']=='draft' and tariff['contract_id']==contract['id'] and eligible and upload['status']=='extracted' and len(entries)==1
                    private_json(Path(env['MCIAS_LAPTOP_STATE_DIR'])/'laptop-smoke.json',
                        {key:entries[0][key] for key in ('claim_reference','claimed_amount')}|{'claim_id':entries[0]['id']})
                    controls.append({'control':'synthetic_reference_upload_import','status':'PASS' if valid else 'BLOCKED'})
                request('/api/v1/auth/logout',{},token)
                controls.append({'control':name+'_mfa_and_permissions','status':'PASS' if
                    missing_denied and replay_denied and separated and admin_access else 'BLOCKED'})
            except Exception:
                controls.append({'control':name+'_mfa_and_permissions','status':'BLOCKED'})
    return {'status':'TEST_CHECKS_PASS' if all(x['status']=='PASS' for x in controls) else 'BLOCKED',
            'synthetic':True,'production_accepted':False,'controls':controls}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Synthetic local laptop tools; not production provisioning')
    parser.add_argument('action',choices=['setup','check','credentials'])
    parser.add_argument('--verify-mfa',action='store_true',help='Fresh-install integration check; wait for a new TOTP counter before repeating')
    parser.add_argument('--verify-inputs',action='store_true',help='With --verify-mfa, add synthetic draft references and one imported claim to test persistence')
    args=parser.parse_args(argv);env=dict(os.environ)
    try:
        guard(env)
        if args.verify_mfa and args.action!='check': raise ValueError('MFA checks require check action')
        if args.verify_inputs and not args.verify_mfa: raise ValueError('Input integration checks require MFA verification')
        if args.action=='setup':
            from alembic import command
            from alembic.config import Config
            os.environ['MCIAS_TEST_DATABASE_URL']=env['MCIAS_E2E_DATABASE_URL']
            command.upgrade(Config('alembic.ini'),'head')
            outcome=setup(env)
        elif args.action=='check': outcome=check(env,verify_mfa=args.verify_mfa,verify_inputs=args.verify_inputs)
        else:
            # Explicit private-console action, never called by setup/check/logs/CI.
            path=Path(env['MCIAS_LAPTOP_STATE_DIR'])/'laptop-credentials.json'
            if path.is_symlink(): raise ValueError('symbolic private state')
            outcome=json.loads(path.read_text())
        print(json.dumps(outcome,ensure_ascii=False,indent=2))
        return 0 if outcome.get('status')!='BLOCKED' else 2
    except Exception:
        print(json.dumps({'status':'BLOCKED','reason':'Local test setup/check failed. Verify keys, private volumes, database and service readiness; secrets are not logged.'}))
        return 2

if __name__=='__main__': raise SystemExit(main())
