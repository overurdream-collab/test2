"""Explicit synthetic browser fixtures; never imported by runtime or normal Seed."""
import argparse, importlib.util, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from mcias.models import MFAFactor

ROOT=Path(__file__).resolve().parents[1]

def run(base_url,chromium):
    url=os.environ['MCIAS_E2E_DATABASE_URL']
    if os.getenv('MCIAS_ENVIRONMENT')!='development' or not make_url(url).database.endswith('_e2e'):
        raise ValueError('dedicated synthetic browser database required')
    server_key=bytes.fromhex(os.environ['MCIAS_MFA_ENCRYPTION_KEY'])
    spec=importlib.util.spec_from_file_location('feature_browser_identities',ROOT/'tests/api/conftest.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    patch=pytest.MonkeyPatch()
    generator=module.api_factory.__wrapped__(patch,module.synthetic_password_hash.__wrapped__())
    try:
        make=next(generator);actor=make(url=url)
        # The existing API fixture uses its own key. Match the already running server.
        with Session(actor.engine) as db:
            factor=db.scalar(select(MFAFactor).where(MFAFactor.user_id==actor.ids['root']))
            nonce=os.urandom(12)
            factor.encrypted_secret=nonce+AESGCM(server_key).encrypt(nonce,actor.mfa_secret,actor.ids['root'].encode())
            db.commit()
        fixture={'username':actor.root_username,'password':actor.password,'organization_id':actor.organization_id,
            'other_organization_id':actor.other_organization_id,'headers':actor.headers,'mfa_secret':actor.mfa_secret.hex()}
    finally:
        generator.close();patch.undo()
    output=ROOT/'.e2e-output/features';output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mcias-private-browser-') as private:
        path=Path(private)/'identities.json';path.write_text(json.dumps(fixture));path.chmod(0o600)
        for name in ('check_features_browser.py','check_feature_navigation.py','check_reference_intake_browser.py'):
            # Password + MFA login replay prevention remains enabled throughout.
            if name=='check_reference_intake_browser.py':time.sleep(31-time.time()%30)
            command=[sys.executable,str(ROOT/'scripts'/name),'--base-url',base_url,'--fixture',str(path),'--output',str(output)]
            if chromium:command+=['--chromium',chromium]
            subprocess.run(command,cwd=ROOT,check=True)
    for path in output.iterdir():
        if path.suffix in ('.json','.png'):shutil.copyfile(path,ROOT/'.e2e-output'/('features-'+path.name))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'));args=parser.parse_args()
    run(args.base_url,args.chromium)
