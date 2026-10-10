"""Read-only target checks must fail closed without disclosing private values."""
import importlib.util
import json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('deploy_check',Path(__file__).resolve().parents[1]/'scripts/deploy_check.py')
check=importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

@pytest.mark.parametrize('origin', ['http://example.org','https://user:secret@example.org','https://example.org/api','https://example.org?token=secret','https://example.org#fragment','https://example.org:invalid','https://example.org\n'])
def test_invalid_target_origins(origin):
    assert not check.valid_origin(origin,'test')

@pytest.mark.parametrize('origin', ['http://127.0.0.1:8000','http://[::1]:8000','https://institution.example'])
def test_safe_origins(origin):
    assert check.valid_origin(origin,'test')
    if origin.startswith('http:'):
        assert not check.valid_origin(origin,'production')

def test_public_checks_only_and_production_docs():
    paths=[]
    def fetch(origin,path,ca):
        paths.append(path)
        if path.startswith('/health/'):
            return 200,{},json.dumps({'status':'ok' if path.endswith('live') else 'ready'}).encode()
        if path=='/login':
            return 200,{'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':"frame-ancestors 'none'"},b''
        return 404,{},b''
    results=check.health_checks('https://institution.example',None,True,fetch)
    assert all(c['status']=='PASS' for c in results)
    assert paths==['/health/live','/health/ready','/login','/docs','/redoc','/openapi.json']

@pytest.mark.parametrize('response',[(302,{},b'private'),(200,{},b'x'*4097),(200,{},b'not json')])
def test_bad_health_responses_block_without_echo(response):
    outcome=check.health_checks('https://institution.example',None,False,lambda *a:response)
    assert outcome[0]['status']=='BLOCKED'
    assert 'private' not in json.dumps(outcome)

def test_no_redirect_following():
    assert check.NoRedirect().redirect_request(None,None,302,'',{},'https://other.example') is None

def test_skipped_database_cannot_pass_and_secrets_are_not_emitted(monkeypatch,tmp_path):
    import mcias.preflight_g9 as preflight
    monkeypatch.setattr(check.subprocess,'check_output',lambda args,**kw:'a'*40 if args[1]=='rev-parse' else '')
    monkeypatch.setattr(check,'health_checks',lambda *a:[])
    def forbidden(*args):
        pytest.fail('database must not be probed when explicitly skipped')
    monkeypatch.setattr(preflight,'check_postgres_role',forbidden)
    tmp_path.chmod(0o700)
    env={'MCIAS_RELEASE_COMMIT':'a'*40,'MCIAS_ENVIRONMENT':'development','MCIAS_DATABASE_URL':'postgresql+psycopg://u:private_password@localhost/test_e2e','MCIAS_STORAGE_DIR':str(tmp_path),'MCIAS_STORAGE_KEY':'1a'*32,'MCIAS_MFA_ENCRYPTION_KEY':'2b'*32}
    outcome=check.run_checks(env,profile='test',origin='http://localhost',expected_commit='a'*40,skip_database=True)
    assert outcome['status']=='BLOCKED' and outcome['production_accepted'] is False
    assert 'private_password' not in json.dumps(outcome)
    assert not list(tmp_path.iterdir())

def test_scanner_rejects_remote_host_without_connecting(monkeypatch):
    monkeypatch.setattr(check.socket,'create_connection',lambda *a,**kw:pytest.fail('remote scanner connection forbidden'))
    assert check.scanner_check({'MCIAS_MALWARE_SCAN':'clamav','MCIAS_CLAMAV_HOST':'remote.example'})['status']=='BLOCKED'

def test_http_redirect_is_not_followed_on_real_server():
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading
    seen=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append((self.path,self.headers.get('Authorization')))
            self.send_response(302)
            self.send_header('Location','/private-records')
            self.end_headers()
            self.wfile.write(b'private response text')
        def log_message(self,*args):
            pass
    server=HTTPServer(('127.0.0.1',0),Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    try:
        status,_,body=check.fetch(f'http://127.0.0.1:{server.server_port}','/health/live')
        assert status==302 and body==b''
        assert seen==[('/health/live',None)]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
