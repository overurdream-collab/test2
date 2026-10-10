"""G5 synthetic, non-production policy registry.

Policies remain unapproved unless an institution supplies a separately verified
authorization. This registry supports drafting, review, and reproducible tests.
"""
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
import json
from mcias.audit_engine import AuditPolicy,PolicyBlocked
from mcias.audit_service import fingerprint_policy

@dataclass(frozen=True)
class PolicyDraft:
    policy: AuditPolicy
    organization_id: str
    author_id: str
    source_document_id: str | None
    status: str="draft"

    def __post_init__(self):
        if self.status!="draft" or self.policy.approved:
            raise PolicyBlocked("draft policy cannot impersonate signed approval")
        if not self.organization_id or not self.author_id:
            raise PolicyBlocked("policy draft requires organization and author")

def policy_preview(draft:PolicyDraft):
    p=draft.policy
    return {"status":"draft","organization_id":draft.organization_id,
            "policy_id":p.policy_id,"source_document_id":draft.source_document_id,
            "requires_authorization":True,
            "rules":{"currency":p.currency,"rounding":p.rounding,"precision":p.precision,
                "order":list(p.order),"copay_percent":str(p.copay_percent),
                "cap":None if p.cap is None else str(p.cap),
                "exclusion":str(p.exclusion),"tariff":str(p.tariff)}}

def synthetic_policy(*,currency="YER"):
    """Only a test fixture; never enable on real claims."""
    return AuditPolicy(policy_id="SYNTHETIC-NOT-AUTHORIZED",currency=currency,
        rounding="HALF_UP",precision=2,
        order=("exclusion","tariff","cap","copay"),
        copay_percent=Decimal("20"),cap=Decimal("80"),
        exclusion=Decimal("10"),tariff=Decimal("100"),approved=False)
