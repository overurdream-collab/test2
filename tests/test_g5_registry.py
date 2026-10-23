"""G5 persisted grant negative tests."""
from types import SimpleNamespace
import pytest
from mcias.audit_engine import PolicyBlocked
from mcias.audit_policy_registry import resolve_grant

class FakeDB:
    def __init__(self,grant): self.grant=grant
    def scalar(self,query): return self.grant
    def get(self,model,key): return self.users.get(key)

def grant(**kw):
    data=dict(organization_id="org1",policy_fingerprint="fingerprint",
              policy_id="policy1",approver_id="head",reviewer_id="reviewer",
              revoked_at=None,signature="signature")
    data.update(kw)
    return SimpleNamespace(**data)

def test_g5_missing_grant_blocks():
    with pytest.raises(PolicyBlocked,match="active institutional"):
        resolve_grant(FakeDB(None),organization_id="org1",
                      policy_fingerprint="fingerprint",policy_id="policy1")

def test_g5_revoked_grant_blocks():
    with pytest.raises(PolicyBlocked,match="active institutional"):
        resolve_grant(FakeDB(grant(revoked_at="2026-10-10")),organization_id="org1",
                      policy_fingerprint="fingerprint",policy_id="policy1")

def test_g5_cross_tenant_signer_blocks():
    db=FakeDB(grant())
    db.users={"head":SimpleNamespace(id="head",active=True,organization_id="org1"),
              "reviewer":SimpleNamespace(id="reviewer",active=True,organization_id="org2")}
    with pytest.raises(PolicyBlocked,match="signers invalid"):
        resolve_grant(db,organization_id="org1",
                      policy_fingerprint="fingerprint",policy_id="policy1")

def test_g5_invalid_signature_blocks(monkeypatch):
    monkeypatch.setenv("MCIAS_G5_POLICY_VERIFICATION_KEY","x"*40)
    # Isolate signature verification; unified RBAC is exercised with real DBs separately.
    monkeypatch.setattr("mcias.audit_policy_registry.has_permission",lambda *args: True)
    db=FakeDB(grant())
    db.users={"head":SimpleNamespace(id="head",active=True,organization_id="org1"),
              "reviewer":SimpleNamespace(id="reviewer",active=True,organization_id="org1")}
    with pytest.raises(PolicyBlocked,match="signature verification failed"):
        resolve_grant(db,organization_id="org1",
                      policy_fingerprint="fingerprint",policy_id="policy1")
