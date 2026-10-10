from dataclasses import replace
from decimal import Decimal
import pytest
from mcias.policy_drafts import PolicyDraft, policy_preview, synthetic_policy
from mcias.audit_engine import PolicyBlocked, evaluate

def test_synthetic_policy_is_not_authorized():
    p=synthetic_policy()
    assert p.approved is False
    with pytest.raises(PolicyBlocked):
        evaluate(Decimal("200"),"YER",p,eligible=True,evidence_complete=True,
            source_id="source",contract_id="contract",beneficiary_enrollment_id="enrollment")

def test_policy_draft_remains_draft():
    p=synthetic_policy()
    d=PolicyDraft(policy=p,organization_id="org",author_id="author",source_document_id=None)
    view=policy_preview(d)
    assert view["status"]=="draft"
    assert view["requires_authorization"] is True
    with pytest.raises(PolicyBlocked):
        PolicyDraft(policy=replace(p,approved=True),organization_id="org",
                    author_id="author",source_document_id=None)

def test_policy_draft_requires_author():
    with pytest.raises(PolicyBlocked):
        PolicyDraft(policy=synthetic_policy(),organization_id="org",
                    author_id="",source_document_id=None)
