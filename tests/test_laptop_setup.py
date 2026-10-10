"""Local test provisioning must stay gated and preserve private credentials."""
import json
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
