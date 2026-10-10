"""G6 preparatory, pure governance decision planning; no production activation.

Only independently verified G5 snapshots may be proposed. Held items are
excluded from partial approvals. Original audit snapshots are never changed.
"""
from dataclasses import dataclass
from hashlib import sha256
import json

class GovernanceBlocked(ValueError):
    pass

@dataclass(frozen=True)
class DecisionProposal:
    organization_id: str
    proposer_id: str
    snapshot_ids: tuple[str,...]
    held_ids: tuple[str,...]
    approval_stages: tuple[str,...]
    evidence_ids: tuple[str,...]

    def validate(self):
        if not self.organization_id or not self.proposer_id:
            raise GovernanceBlocked("tenant and proposer required")
        if not self.approval_stages or len(set(self.approval_stages))!=len(self.approval_stages):
            raise GovernanceBlocked("independent approval stages required")
        if not self.snapshot_ids or len(set(self.snapshot_ids))!=len(self.snapshot_ids):
            raise GovernanceBlocked("unique audit snapshots required")
        if set(self.held_ids)-set(self.snapshot_ids):
            raise GovernanceBlocked("held items must belong to proposal")

def plan_decision(proposal:DecisionProposal, *, actor_id:str, stage:str,
                  verified_snapshot_ids:tuple[str,...], previous_version:int=0):
    proposal.validate()
    if actor_id==proposal.proposer_id:
        raise GovernanceBlocked("T11 proposer cannot approve own decision")
    if stage not in proposal.approval_stages:
        raise GovernanceBlocked("unconfigured approval stage")
    if previous_version<0:
        raise GovernanceBlocked("invalid decision version")
    verified=set(verified_snapshot_ids)
    if not verified.issubset(set(proposal.snapshot_ids)):
        raise GovernanceBlocked("unrelated audit snapshot")
    approved=tuple(s for s in proposal.snapshot_ids if s in verified and s not in proposal.held_ids)
    held=tuple(s for s in proposal.snapshot_ids if s not in approved)
    payload={"organization_id":proposal.organization_id,"actor_id":actor_id,
             "stage":stage,"version":previous_version+1,
             "approved_ids":approved,"held_ids":held,
             "evidence_ids":proposal.evidence_ids}
    payload["fingerprint"]=sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    return payload

def objection_impact(*, original_snapshot_ids, objection_evidence_id, affected_snapshot_ids):
    if not objection_evidence_id:
        raise GovernanceBlocked("T10 objection source evidence required")
    original=set(original_snapshot_ids)
    affected=set(affected_snapshot_ids)
    if not affected or not affected.issubset(original):
        raise GovernanceBlocked("objection must target existing audited items")
    return {"source_evidence_id":objection_evidence_id,
            "reaudit_required_ids":tuple(sorted(affected)),
            "unchanged_ids":tuple(sorted(original-affected)),
            "original_snapshot_ids":tuple(original_snapshot_ids)}
