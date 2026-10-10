"""G5 lifecycle adversarial tests: no privilege, no self approval, no bypass."""
from types import SimpleNamespace
import pytest
from mcias.audit_engine import PolicyBlocked
from mcias.audit_policy_lifecycle import enroll_grant,revoke_grant

def test_g5_enroll_denies_unauthorized_actor_before_database(monkeypatch):
    monkeypatch.setattr("mcias.audit_policy_lifecycle.has_permission",lambda *args:False)
    actor=SimpleNamespace(id="a",active=True,organization_id="org")
    with pytest.raises(PolicyBlocked,match="permission"):
        enroll_grant(None,actor=actor,organization_id="org",policy_id="p",
            policy_fingerprint="f",approver_id="a",reviewer_id="b",signature="sig")

def test_g5_enroll_denies_cross_tenant_before_database(monkeypatch):
    monkeypatch.setattr("mcias.audit_policy_lifecycle.has_permission",lambda *args:True)
    actor=SimpleNamespace(id="a",active=True,organization_id="other")
    with pytest.raises(PolicyBlocked,match="permission"):
        enroll_grant(None,actor=actor,organization_id="org",policy_id="p",
            policy_fingerprint="f",approver_id="a",reviewer_id="b",signature="sig")

def test_g5_enroll_denies_impersonated_approver_before_database(monkeypatch):
    monkeypatch.setattr("mcias.audit_policy_lifecycle.has_permission",lambda *args:True)
    actor=SimpleNamespace(id="intruder",active=True,organization_id="org")
    with pytest.raises(PolicyBlocked,match="permission"):
        enroll_grant(None,actor=actor,organization_id="org",policy_id="p",
            policy_fingerprint="f",approver_id="a",reviewer_id="b",signature="sig")
