"""G5 orchestration; policy is supplied by authorized configuration, never inferred."""
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
import json
from sqlalchemy import select
from mcias.audit_engine import AuditPolicy,PolicyBlocked,evaluate
from mcias.audit_authorization import VerifiedPolicyAuthorization, verify_registered_policy
from mcias.audit_policy_registry import resolve_grant
from mcias.audit_agents import inspect_claim
from mcias.palermo2 import verify
from mcias.models_claims import ClaimBatch, ClaimEntry
from mcias.models_audit import AuditSnapshot

def fingerprint_policy(policy):
    policy.validate()
    d={key:(str(value) if isinstance(value,Decimal) else list(value) if isinstance(value,tuple) else value)
       for key,value in asdict(policy).items()}
    return sha256(json.dumps(d,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def run_audit(db,actor,claim_id,policy:AuditPolicy=None,*,verified_authorization=None,review_only=False,
              a1_review_packet=None,evidence_store=None):
    if type(review_only) is not bool:
        raise PolicyBlocked("review_only must be an explicit boolean")
    if review_only:
        return _run_inputs_first_review(db, actor, claim_id, a1_review_packet, evidence_store)
    if a1_review_packet is not None or evidence_store is not None:
        raise PolicyBlocked("A1 evidence is restricted to advisory review_only execution")
    # The caller must supply a verified, tenant-bound authorization from a
    # trusted G1 signer; a client-side 'approved=True' flag is insufficient.
    # A caller-supplied dictionary is not proof of a cryptographic signature.
    # Only a server-verified authorization object from the trusted verifier
    # may authorize a financial snapshot.
    if type(verified_authorization) is not VerifiedPolicyAuthorization:
        raise PolicyBlocked('verified institutional policy authorization required (trusted server-side verification)')
    if (verified_authorization.organization_id!=getattr(actor,'organization_id',None)
        or verified_authorization.policy_fingerprint!=fingerprint_policy(policy)
        or not verified_authorization.signature_verified
        or not verified_authorization.independent_reviewer_verified):
        raise PolicyBlocked('policy authorization is invalid or not independently reviewed')
    if not actor.active or not actor.organization_id:
        raise PolicyBlocked("authorized active organization required")
    try:
        registered=verify_registered_policy(db,organization_id=actor.organization_id,
            policy_fingerprint=fingerprint_policy(policy))
    except ValueError as exc:
        raise PolicyBlocked(str(exc)) from exc
    if registered != verified_authorization:
        raise PolicyBlocked('authorization must match active institutional registry')
    # Re-check durable institutional authorization on every execution,
    # including after a policy grant has been revoked.
    registered_grant=resolve_grant(db,organization_id=actor.organization_id,
        policy_fingerprint=fingerprint_policy(policy),policy_id=policy.policy_id)
    if registered_grant != verified_authorization:
        raise PolicyBlocked('institutional policy grant mismatch')
    claim=db.scalar(select(ClaimEntry).where(ClaimEntry.id==claim_id,
        ClaimEntry.organization_id==actor.organization_id).with_for_update())
    if claim is None:
        raise PolicyBlocked("claim not accessible")
    fp=fingerprint_policy(policy)
    existing=db.scalar(select(AuditSnapshot).where(AuditSnapshot.claim_id==claim.id,
        AuditSnapshot.policy_fingerprint==fp))
    checks=inspect_claim(db,claim,policy,actor=actor)
    if existing:
        if "audit_state" not in existing.findings:
            raise PolicyBlocked("legacy snapshot lacks INPUTS-FIRST evidence; a new policy version is required")
        if any(existing.findings.get(key)!=checks[key] for key in
               ("audit_state","source_evidence","reference_certificates")):
            raise PolicyBlocked("snapshot evidence changed; a new policy version is required")
        return existing
    blocked=(checks["audit_state"]!="VERIFIED_MATCH" or checks["review_required"]
        or checks["tariff"] is None or checks["contract"] is None)
    if blocked:
        calculation={"status":"held","reason":"unresolved_reference_or_evidence",
            "claimed":str(claim.claimed_amount),"payable":None,"deductions":[],
            "policy_id":policy.policy_id,"source_id":claim.extracted_record_id}
    else:
        # A G3 tariff is an upper-bound candidate; the financial policy must
        # explicitly match the approved tariff, never silently substitute it.
        if checks["tariff"].amount!=policy.tariff:
            raise PolicyBlocked("financial policy tariff differs from approved G3 tariff")
        calculation=evaluate(claim.claimed_amount,claim.currency,policy,
            eligible=checks["eligible"],evidence_complete=checks["evidence_complete"],
            source_id=claim.extracted_record_id,contract_id=checks["contract"].id,
            beneficiary_enrollment_id=checks["enrollment"].id)
    verification=verify(claim,checks["findings"],calculation)
    snapshot=AuditSnapshot(organization_id=claim.organization_id,claim_id=claim.id,
        policy_id=policy.policy_id,policy_fingerprint=fp,calculation=calculation,
        findings={"agents":checks["findings"],"audit_state":checks["audit_state"],
            "reference_certificates":checks["reference_certificates"],
            "source_evidence":checks["source_evidence"],"coverage":checks["coverage"],
            "human_review_required":checks["review_required"],"financial_decision":"not_authorized"},
        verification=verification,created_by=actor.id)
    db.add(snapshot);db.flush()
    from mcias.audit_writer import write_event
    from mcias.models_ingestion import IngestionDocument
    batch=db.get(ClaimBatch,claim.batch_id)
    document=db.get(IngestionDocument,batch.ingestion_document_id)
    references=[]
    for certificate in checks["reference_certificates"]:
        evidence_ids=sorted({evidence[key] for evidence in certificate["source_evidence"]
            for key in ("source_id","authorization_id") if evidence.get(key)})
        references.append({"family":certificate["family"],"id":certificate["reference_id"],
            "version":certificate["version"],"status":certificate["lookup_status"],
            "evidence_ids":evidence_ids,"gaps":certificate["gaps"]})
    write_event(db,actor=actor,organization_id=claim.organization_id,
        action="claim_inputs_audited",resource_type="claim_entry",resource_id=claim.id,
        outcome="success",details={"audit_snapshot_id":snapshot.id,
            "source_record_id":claim.extracted_record_id,"document_id":document.id,
            "source_sha256":batch.source_sha256,"policy_fingerprint":fp,
            "audit_state":checks["audit_state"],"references":references})
    db.commit()
    return snapshot


def _review_findings_identity(findings):
    """Exclude only unverified A1 execution trace from advisory result identity.

    Preserve every source, value, rule, version, outcome and verification flag.
    The first immutable snapshot retains its complete original trace metadata.
    """
    from copy import deepcopy
    result = deepcopy(findings)
    for finding in result.get("agents", []):
        if finding.get("agent") == "evidence" and isinstance(finding.get("a1_evidence"), dict):
            for key in ("a1_input_fingerprint", "a1_output_fingerprint", "audit_run_id"):
                finding["a1_evidence"].pop(key, None)
    return result


def _run_inputs_first_review(db, actor, claim_id, a1_review_packet=None, evidence_store=None):
    """Persist existing INPUTS-FIRST findings without authorizing any payment.

    The existing Super Admin and claims.read grants are checked on the durable
    user. This service extension does not expose a new API or financial policy.
    """
    from mcias.models import User, Role, UserRole
    from mcias.policy import has_permission
    from mcias.audit_contract import claim_reference_projection
    from mcias.audit_writer import write_event
    user = db.get(User, getattr(actor, "id", None))
    role = db.scalar(select(Role.id).join(UserRole, UserRole.role_id == Role.id).where(
        UserRole.user_id == getattr(user, "id", None), Role.code == "super_admin"))
    if (user is None or not user.active or not user.organization_id or not role
        or not has_permission(db, user, "claims.read")):
        raise PolicyBlocked("active Super Admin with claims.read required for advisory execution")
    claim = db.scalar(select(ClaimEntry).where(ClaimEntry.id == claim_id,
        ClaimEntry.organization_id == user.organization_id).with_for_update())
    if claim is None:
        raise PolicyBlocked("claim not accessible")
    checks = inspect_claim(db, claim, actor=user, review_only=True,
        a1_review_packet=a1_review_packet, evidence_store=evidence_store)
    findings = {"agents": checks["findings"], "audit_state": checks["audit_state"],
        "audit_state_schema_version": 2, "reason_code": checks["reason_code"],
        "reference_certificates": checks["reference_certificates"],
        "source_evidence": checks["source_evidence"], "coverage": checks["coverage"],
        "human_review_required": True, "financial_decision": "not_authorized"}
    # Fingerprint the actual validated source, versions and findings. Replaying
    # the same evidence returns one immutable snapshot/event; a later trusted
    # reference version creates a separate traceable snapshot.
    identity = _review_findings_identity(findings)
    context = {"mode": "inputs_first_review", "schema_version": 2,
        "claim_id": claim.id, "findings": identity}
    fp = sha256(json.dumps(context, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    existing = db.scalar(select(AuditSnapshot).where(AuditSnapshot.claim_id == claim.id,
        AuditSnapshot.policy_fingerprint == fp))
    if existing is not None:
        if _review_findings_identity(existing.findings) != identity:
            raise PolicyBlocked("immutable review snapshot differs from its evidence")
        return existing
    calculation = {"status": "held", "reason": "advisory_review_only",
        "mode": "inputs_first_review", "claimed": str(claim.claimed_amount),
        "currency": claim.currency, "payable": None, "deductions": [],
        "financial_decision": "not_authorized", "source_id": claim.extracted_record_id}
    verification = verify(claim, checks["findings"], calculation)
    snapshot = AuditSnapshot(organization_id=claim.organization_id, claim_id=claim.id,
        policy_id="inputs-first-review-v2", policy_fingerprint=fp,
        calculation=calculation, findings=findings, verification=verification, created_by=user.id)
    db.add(snapshot)
    db.flush()
    batch = db.get(ClaimBatch, claim.batch_id)
    write_event(db, actor=user, organization_id=claim.organization_id,
        action="claim_inputs_audited", resource_type="claim_entry", resource_id=claim.id,
        outcome="success", details={"audit_snapshot_id": snapshot.id,
            "source_record_id": claim.extracted_record_id, "document_id": batch.ingestion_document_id,
            "source_sha256": batch.source_sha256, "policy_fingerprint": fp,
            "audit_state_schema_version": 2, "audit_state": checks["audit_state"],
            "reason_code": checks["reason_code"],
            "references": claim_reference_projection(checks["reference_certificates"])})
    db.commit()
    return snapshot
