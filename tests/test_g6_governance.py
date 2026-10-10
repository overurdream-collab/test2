"""G6 guard regression without exposing production approval endpoints."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from mcias.governance_cases import GovernanceBlocked, decide

def test_g6_rejects_invalid_decisions_before_db_access():
    with pytest.raises(GovernanceBlocked,match="invalid decision"):
        decide(None,SimpleNamespace(id="u"),"case",stage="review",decision="paid",evidence={})

def test_g6_rejects_self_approval():
    case=SimpleNamespace(id="c",organization_id="org",proposed_by="u",state="pending")
    db=MagicMock()
    db.scalar.return_value=case
    with pytest.raises(GovernanceBlocked,match="self approval"):
        decide(db,SimpleNamespace(id="u",organization_id="org",active=True),
            "c",stage="review",decision="approved",evidence={})

def test_g6_rejects_closed_case():
    case=SimpleNamespace(id="c",organization_id="org",proposed_by="p",state="approved")
    db=MagicMock()
    db.scalar.return_value=case
    with pytest.raises(GovernanceBlocked,match="not pending"):
        decide(db,SimpleNamespace(id="reviewer",organization_id="org",active=True),
            "c",stage="review",decision="approved",evidence={})

def test_g6_held_snapshot_cannot_be_approved():
    case=SimpleNamespace(id="c",organization_id="org",proposed_by="p",state="pending",
        audit_snapshot_id="s")
    db=MagicMock()
    db.scalar.return_value=case
    db.get.return_value=SimpleNamespace(organization_id="org",
        calculation={"status":"held"},verification={"status":"held"})
    with pytest.raises(GovernanceBlocked,match="cannot be approved"):
        decide(db,SimpleNamespace(id="reviewer",organization_id="org",active=True),
            "c",stage="review",decision="approved",evidence={})
