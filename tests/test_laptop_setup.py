"""Local test provisioning must stay gated and preserve private credentials."""
import json
import os
from pathlib import Path
import subprocess
import pytest
from mcias.seed.laptop import guard, private_json, ADMIN_PERMISSIONS, REVIEWER_PERMISSIONS

def env():
    return {'MCIAS_LAPTOP_TEST_MODE':'synthetic_localhost','MCIAS_ENVIRONMENT':'development',
      'MCIAS_DATABASE_URL':'postgresql+psycopg://laptop_runtime:synthetic@localhost/mcias_laptop_e2e',
      'MCIAS_MFA_ENCRYPTION_KEY':'1a'*32,'MCIAS_STORAGE_KEY':'2b'*32}

@pytest.mark.parametrize('key,value',[
 ('MCIAS_ENVIRONMENT','production'),('MCIAS_LAPTOP_TEST_MODE',''),
 ('MCIAS_DATABASE_URL','sqlite:///mcias_laptop_e2e'),
 ('MCIAS_DATABASE_URL','postgresql+psycopg://laptop_runtime:p@localhost/customer'),
 ('MCIAS_DATABASE_URL','postgresql+psycopg://laptop_owner:p@localhost/mcias_laptop_e2e'),
 ('MCIAS_MFA_ENCRYPTION_KEY','00'*32),('MCIAS_STORAGE_KEY','invalid')])
def test_reject_unsafe_profiles(key,value):
    values=env();values[key]=value
    with pytest.raises(ValueError): guard(values)

def test_valid_local_profile_and_duty_separation():
    assert guard(env()).database=='mcias_laptop_e2e'
    assert 'governance.propose' in ADMIN_PERMISSIONS
    assert 'governance.approve' not in ADMIN_PERMISSIONS
    assert 'governance.approve' in REVIEWER_PERMISSIONS
    assert not any(p.startswith('medical_fields.') for p in ADMIN_PERMISSIONS+REVIEWER_PERMISSIONS)
    assert 'policies.approve' not in ADMIN_PERMISSIONS

def test_private_receipt_and_symlink_denial(tmp_path):
    path=tmp_path/'state'/'credentials.json'
    private_json(path,{'synthetic':True})
    assert json.loads(path.read_text())=={'synthetic':True}
    assert path.stat().st_mode & 0o777 == 0o600
    path.unlink();path.symlink_to(tmp_path/'not-written')
    with pytest.raises(ValueError): private_json(path,{'secret':'no'})
    assert not (tmp_path/'not-written').exists()


@pytest.mark.parametrize('failures,attempts,succeeds', [
    (0, 1, True), (1, 2, True), (2, 3, True), (3, 3, False), (99, 3, False),
])
def test_dependency_install_retries_are_bounded(tmp_path, failures, attempts, succeeds):
    """Run the Dockerfile's actual retry loop without network or system changes."""
    dockerfile = (Path(__file__).resolve().parents[1] / 'deploy/Dockerfile.laptop').read_text()
    loop = dockerfile.split('    install_attempt=1;', 1)[1].split('    done', 1)[0]
    loop = ('install_attempt=1;' + loop + 'done').replace('\\\n', '\n')
    fake_python = tmp_path / 'python'
    fake_python.write_text('''#!/bin/sh
count=0
if [ -f "$RETRY_STATE/count" ]; then read -r count < "$RETRY_STATE/count"; fi
count=$((count + 1))
echo "$count" > "$RETRY_STATE/count"
echo "$*" >> "$RETRY_STATE/arguments"
test "$count" -gt "$RETRY_FAILURES"
''')
    fake_sleep = tmp_path / 'sleep'
    fake_sleep.write_text('#!/bin/sh\necho "$*" >> "$RETRY_STATE/sleeps"\n')
    fake_python.chmod(0o700)
    fake_sleep.chmod(0o700)
    result = subprocess.run(
        ['/bin/sh', '-c', loop + '\n echo INSTALL_COMPLETED'],
        env={**os.environ, 'PATH': f'{tmp_path}:{os.environ["PATH"]}',
             'RETRY_STATE': str(tmp_path), 'RETRY_FAILURES': str(failures)},
        capture_output=True, text=True, timeout=5,
    )
    assert int((tmp_path / 'count').read_text()) == attempts
    assert (tmp_path / 'arguments').read_text().splitlines() == [
        '-m pip install --timeout 180 --retries 10 .'
    ] * attempts
    sleeps = tmp_path / 'sleeps'
    assert (sleeps.read_text().splitlines() if sleeps.exists() else []) == ['10'] * (attempts - 1)
    assert result.returncode == (0 if succeeds else 1)
    assert ('INSTALL_COMPLETED' in result.stdout) == succeeds
    if not succeeds:
        assert 'failed after 3 attempts' in result.stderr
