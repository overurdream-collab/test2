"""Signed G5 policy authorization and strict fail-closed tests."""
import hashlib
import hmac
from types import SimpleNamespace
import pytest
from mcias.audit_authorization import verify_policy_authorization
from mcias.audit_engine import PolicyBlocked
from mcias.audit_service import run_audit

def test_g5_policy_signature_valid(monkeypatch):
    key="local-only-"+"x"*40
    monkeypatch.setenv("MCIAS_G5_POLICY_VERIFICATION_KEY",key)
    payload="org1|fingerprint1|head1|reviewer2".encode()
    sig=hmac.new(key.encode(),payload,hashlib.sha256).hexdigest()
    result=verify_policy_authorization(organization_id="org1",policy_fingerprint="fingerprint1",
        approver_id="head1",reviewer_id="reviewer2",signature=sig)
    assert result.signature_verified and result.independent_reviewer_verified

@pytest.mark.parametrize("approver,reviewer,signature",[
    ("head1","head1","deadbeef"),("head1","reviewer2","deadbeef")])
def test_g5_rejects_unverified_or_self_approved_policy(monkeypatch,approver,reviewer,signature):
    monkeypatch.setenv("MCIAS_G5_POLICY_VERIFICATION_KEY","x"*40)
    with pytest.raises(ValueError):
        verify_policy_authorization(organization_id="org1",policy_fingerprint="fp",
            approver_id=approver,reviewer_id=reviewer,signature=signature)

def test_g5_missing_server_key_fails_closed(monkeypatch):
    monkeypatch.delenv("MCIAS_G5_POLICY_VERIFICATION_KEY",raising=False)
    with pytest.raises(ValueError,match="key unavailable"):
        verify_policy_authorization(organization_id="org",policy_fingerprint="fp",
            approver_id="a",reviewer_id="b",signature="bad")

def test_g5_caller_forged_approval_is_rejected_before_database_access():
    actor=SimpleNamespace(active=True,organization_id="org")
    with pytest.raises(PolicyBlocked,match="trusted server-side"):
        run_audit(None,actor,"claim",None,verified_authorization={
            "organization_id":"org","signature_verified":True,
            "independent_reviewer_verified":True})
