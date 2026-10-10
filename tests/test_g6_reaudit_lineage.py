"""G6 T10: re-audit is a linked new snapshot, never an old-record edit."""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from mcias.governance_g6 import GovernanceBlocked, append_event

def actor():
    return SimpleNamespace(id="reviewer",active=True,organization_id="org1")

def oldcase():
    return SimpleNamespace(id="case1", organization_id="org1", opened_by="author",
        claim_id="claim1", audit_snapshot_id="snapshot1")

def last_event(kind):
    return SimpleNamespace(id="old", case_id="case1", actor_id="author",
        kind=kind, version=3)

@patch("mcias.governance_g6.has_permission",return_value=True)
def test_t10_link_requires_prior_recorded_reaudit_request(_permission):
    db = MagicMock()
    db.scalar.side_effect = [oldcase(),last_event("object")]
    with pytest.raises(GovernanceBlocked,match="recorded request"):
        append_event(db,actor(),"case1","link_reaudit",{"new_snapshot_id":"snapshot2"})
    db.commit.assert_not_called()

@patch("mcias.governance_g6.has_permission",return_value=True)
def test_t10_link_denies_cross_tenant_and_unrelated_claim(_permission):
    for org, claim in [("other","claim1"),("org1","another")]:
        db = MagicMock()
        db.scalar.side_effect = [oldcase(),last_event("request_reaudit")]
        db.get.return_value = SimpleNamespace(id="snapshot2",organization_id=org,claim_id=claim)
        with pytest.raises(GovernanceBlocked,match="tenant or claim"):
            append_event(db,actor(),"case1","link_reaudit",{"new_snapshot_id":"snapshot2"})
        db.commit.assert_not_called()

@patch("mcias.governance_g6.has_permission",return_value=True)
def test_t10_link_creates_new_case_and_append_only_event(_permission):
    db = MagicMock()
    db.scalar.side_effect = [oldcase(),last_event("request_reaudit"),None]
    start = datetime(2026, 10, 10, tzinfo=timezone.utc)
    db.get.side_effect = [
        SimpleNamespace(id="snapshot2",organization_id="org1",claim_id="claim1",created_at=start + timedelta(days=1)),
        SimpleNamespace(id="snapshot1",organization_id="org1",claim_id="claim1",created_at=start),
    ]
    event = append_event(db,actor(),"case1","link_reaudit",{"new_snapshot_id":"snapshot2"})
    assert event.kind == "link_reaudit"
    assert event.snapshot_id == "snapshot2"
    assert event.version == 4
    assert event.payload["new_snapshot_id"] == "snapshot2"
    assert db.add.call_count >= 3
    db.commit.assert_called_once()

@patch("mcias.governance_g6.has_permission",return_value=True)
def test_g6_reject_quarantined_objection_evidence(_permission):
    db = MagicMock()
    db.scalar.side_effect = [oldcase(),None]
    db.get.return_value = SimpleNamespace(organization_id="org1",status="quarantined",
        sha256="a"*64)
    with pytest.raises(GovernanceBlocked,match="not verified"):
        append_event(db,actor(),"case1","object",{},evidence_document_id="doc1")
    db.commit.assert_not_called()
