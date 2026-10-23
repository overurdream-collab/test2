"""G5 orchestration; policy is supplied by authorized configuration, never inferred."""
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
import json
from sqlalchemy import select
from mcias.audit_engine import AuditPolicy,PolicyBlocked,evaluate,policy_definition,evaluate_net
from mcias.audit_authorization import VerifiedPolicyAuthorization, verify_registered_policy
from mcias.audit_policy_registry import resolve_grant
from mcias.audit_agents import inspect_claim
from mcias.palermo2 import verify
from mcias.models_claims import ClaimEntry
from mcias.models_audit import AuditSnapshot
from mcias.models import AuditLog

def _require_supported_amount_basis(db,claim):
    from mcias.claim_batches import confirmed_mapping
    from mcias.models_claims import ClaimBatch
    batch=db.get(ClaimBatch,claim.batch_id)
    mapping=confirmed_mapping(db,batch) if batch else None
    if mapping and mapping.get('amount_basis')=='NET':
        raise PolicyBlocked('NET source: use linked reference validation; the gross financial evaluator must not deduct copay again')

def fingerprint_policy(policy):
    d=policy_definition(policy)
    return sha256(json.dumps(d,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def run_audit(db,actor,claim_id,policy:AuditPolicy,*,verified_authorization=None,reference_context=None):
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
        ClaimEntry.organization_id==actor.organization_id))
    if claim is None:
        raise PolicyBlocked("claim not accessible")
    if policy.amount_basis=='GROSS':_require_supported_amount_basis(db,claim)
    from mcias.services.transaction_lock import lock_record
    lock_record(db,'g5_claim_snapshot',actor.organization_id,claim.id)
    if policy.amount_basis=='NET':
        from mcias.services.net_audit_service import inspect_net_claim
        checks=inspect_net_claim(db,actor,claim,policy,reference_context)
        reference_check=checks['reference_check']
        if reference_check['status']=='BLOCKED':
            raise PolicyBlocked('missing_invoice' if not reference_check['invoices'] else 'unresolved_reference_or_evidence')
    fp=fingerprint_policy(policy)
    existing=db.scalar(select(AuditSnapshot).where(AuditSnapshot.claim_id==claim.id,
        AuditSnapshot.policy_fingerprint==fp))
    if existing:
        if policy.amount_basis=='NET' and checks['review_required'] and existing.verification.get('status')=='verified':
            raise PolicyBlocked('Changed review conditions require a separately approved re-audit version')
        if policy.amount_basis=='NET' and existing.calculation.get('status')=='calculated' and existing.calculation.get('invoice_evidence')!=reference_check['invoices']:
            raise PolicyBlocked('Changed invoice evidence requires a separately approved re-audit version')
        return existing
    if policy.amount_basis=='NET':
        if checks['review_required']:
            calculation={'status':'held','reason':'human_review_required','claimed':str(claim.claimed_amount),
                'payable':None,'deductions':[],'policy_id':policy.policy_id,'source_id':claim.extracted_record_id,'amount_basis':'NET'}
        else:calculation=evaluate_net(claim,policy,reference_check)
    else:checks=inspect_claim(db,claim,policy)
    blocked=checks["review_required"] or checks["tariff"] is None or checks["contract"] is None
    if policy.amount_basis=='NET':pass
    elif blocked:
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
    verification=verify(claim,checks["findings"],calculation,policy_fingerprint=fp,
        policy_id=policy.policy_id,reference_check=reference_check if policy.amount_basis=='NET' else None)
    extra={'reference_check':reference_check} if policy.amount_basis=='NET' else {}
    snapshot=AuditSnapshot(organization_id=claim.organization_id,claim_id=claim.id,
        policy_id=policy.policy_id,policy_fingerprint=fp,calculation=calculation,
        findings={"agents":checks["findings"],**extra},verification=verification,created_by=actor.id)
    db.add(snapshot);db.flush()
    db.add(AuditLog(actor_id=actor.id,action="audit_snapshot_created",
        resource_type="audit_snapshot",resource_id=snapshot.id,
        details={"claim_id":claim.id,"policy_fingerprint":fp,
                 "verification_status":verification["status"]}))
    db.commit()
    return snapshot
