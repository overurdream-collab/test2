"""G6 negative authorization and decision immutability tests."""
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
import pytest
from mcias.governance_g6 import GovernanceBlocked,append_event
from mcias.models_governance_g6 import GovernanceEvent

def actor(user_id="user1",org="org1"):
    return SimpleNamespace(id=user_id,active=True,organization_id=org)

def case(opened_by="user1"):
    return SimpleNamespace(id="case1",organization_id="org1",
        opened_by=opened_by,audit_snapshot_id="snap1")

@patch("mcias.governance_g6.has_permission",return_value=True)
def test_g6_t11_self_approval_blocked(permission):
    db=MagicMock()
    db.scalar.side_effect=[case(),SimpleNamespace(kind="propose",actor_id="user2",version=1)]
    with pytest.raises(GovernanceBlocked,match="self approval"):
        append_event(db,actor(),"case1","approve",{})

@patch("mcias.governance_g6.has_permission",return_value=True)
def test_g6_t10_objection_requires_evidence(permission):
    db=MagicMock()
    db.scalar.side_effect=[case(),None]
    with pytest.raises(GovernanceBlocked,match="linked evidence"):
        append_event(db,actor(),"case1","object",{})

@patch("mcias.governance_g6.has_permission",return_value=True)
def test_g6_t12_held_claim_cannot_be_approved(permission):
    db=MagicMock()
    db.scalar.side_effect=[case(),SimpleNamespace(kind="propose",actor_id="user1",version=1)]
    with pytest.raises(GovernanceBlocked):
        append_event(db,actor("reviewer"),"case1","approve",{})

@patch("mcias.governance_g6.has_permission",return_value=True)
def test_g6_final_decision_requires_new_objection(permission):
    db=MagicMock()
    db.scalar.side_effect=[case(),SimpleNamespace(kind="approve",actor_id="reviewer",version=2)]
    with pytest.raises(GovernanceBlocked,match="final decision"):
        append_event(db,actor("user3"),"case1","hold",{})

def test_g6_event_update_rejected():
    with pytest.raises(ValueError,match="append-only"):
        from mcias.models_governance_g6 import immutable_event
        immutable_event(None,None,None)

@patch("mcias.governance_g6.has_permission",return_value=False)
def test_g6_default_deny(permission):
    with pytest.raises(GovernanceBlocked,match="permission"):
        append_event(None,actor(),"case1","approve",{})

@patch("mcias.governance_g6.has_permission",return_value=True)
@pytest.mark.parametrize("snapshot",[
    None,
    SimpleNamespace(organization_id="other",claim_id="claim1",
                    calculation={"status":"calculated"},verification={"status":"verified"}),
    SimpleNamespace(organization_id="org1",claim_id="wrong",
                    calculation={"status":"calculated"},verification={"status":"verified"}),
])
def test_g6_approval_fails_closed_on_missing_or_mismatched_snapshot(permission,snapshot):
    db=MagicMock()
    item=case(opened_by="opener")
    item.claim_id="claim1"
    db.scalar.side_effect=[item,SimpleNamespace(kind="propose",actor_id="proposer",version=1)]
    db.get.return_value=snapshot
    with pytest.raises(GovernanceBlocked):
        append_event(db,actor("reviewer"),"case1","approve",{})
    db.commit.assert_not_called()

@patch('mcias.governance_g6.has_permission',return_value=True)
def test_rejection_also_requires_independent_actor(permission):
    db=MagicMock()
    db.scalar.side_effect=[case(),SimpleNamespace(kind='propose',actor_id='user1',version=1)]
    with pytest.raises(GovernanceBlocked,match='self approval'):
        append_event(db,actor(),'case1','reject',{})
    db.commit.assert_not_called()
