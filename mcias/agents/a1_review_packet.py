"""A1 read-only packet for G6/G7/PR22 triage; no financial or claim decision.

This is a versioned interface, NOT an automatic G6 decision or activated
ReferencePoint. Defer to G5 signed policy and independent Palermo review.
"""
from datetime import datetime, timezone
from copy import deepcopy

SCHEMA_VERSION="mcias.a1.review.v1"

def packet_from_preview(preview):
    if not isinstance(preview,dict) or "a1" not in preview:
        raise ValueError("A1 preview envelope required")
    a1=preview["a1"]
    missing=preview.get("missing_evidence",[])
    if not isinstance(missing,list) or not isinstance(a1.get("findings"),list):
        raise ValueError("invalid A1 evidence contract")
    # The PR22 codes are only provisional dispositions, never final decisions.
    if "no_unique_verified_itemized_invoice" in missing or "attachment_missing_itemized_fields" in missing:
        disposition="MISSING_ATTACHMENTS"
    else:
        disposition="HUMAN_REVIEW"
    def origin(item):
        e=item.get("engine")
        return "AI_ADVISORY" if e=="model" else "RULE_ENGINE" if e=="rules" else "UNCLASSIFIED"
    return {
        "schema_version":SCHEMA_VERSION,
        "tenant_id":a1.get("tenant_id"),
        "claim_id":a1.get("claim_id"),
        "audit_run_id":a1.get("run_id"),
        "a1_input_fingerprint":a1.get("input_fingerprint"),
        "a1_output_fingerprint":a1.get("output_fingerprint"),
        "provisional_four_way_code":disposition,
        "classification_is_final":False,
        "source_verification_status":preview.get("status"),
        # Optional additive producer evidence; consumers must reverify the G2
        # source and rule. A packet assertion never grants financial authority.
        "source_evidence":deepcopy(preview.get("source_evidence")),
        "source_evidence_fingerprint":preview.get("source_evidence_fingerprint"),
        "missing_evidence":sorted(set(missing)),
        "findings":[{"type":f.get("finding_type"),"origin":origin(f),
                     "status":f.get("finding_status"),"line_item_id":f.get("line_item_id"),
                     "evidence_refs":f.get("evidence_refs",[])}
                    for f in a1["findings"]],
        "palermo_independent_financial_verification":"NOT_EXECUTED",
        "signed_g5_financial_policy_fingerprint":None,
        "g6_authorized_reviewer_decision":"PENDING",
        "g7_realized_savings":None,
        "suspected_amounts_added_to_realized_savings":False,
        "financial_decision_authorized":False,
        "produced_at":datetime.now(timezone.utc).isoformat(),
    }
