"""NET integration of existing G4/G5/G6/G7 components; no implicit approval."""
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
import json
from sqlalchemy import select
from mcias.models import AuditLog, SourceFile
from mcias.models_claims import ClaimEntry, ClaimBatch
from mcias.audit_agents import AGENTS
from mcias.audit_engine import AuditPolicy, PolicyBlocked, money, policy_definition
from mcias.audit_service import fingerprint_policy,run_audit
from mcias.audit_authorization import verify_registered_policy
from mcias.claim_batches import confirmed_mapping
from mcias.reporting_g7 import canonical
from mcias.services.claim_reference_service import ReferenceIndex,inspect_line
from mcias.services.registry_service import store
from mcias.services.transaction_lock import lock_record
from mcias.policy import has_permission


def reference_fingerprint(check):
    references={k:v for k,v in check['references'].items() if k!='beneficiary_enrollment'}
    return sha256(canonical(references)).hexdigest()


@dataclass
class NetContext:
    index: ReferenceIndex
    mapping: dict
    batch_id: str


def context_for(db,actor,batch):
    return NetContext(ReferenceIndex(db,actor),confirmed_mapping(db,batch),batch.id)


def inspect_net_claim(db,actor,claim,policy,context=None):
    if context is None:context=context_for(db,actor,db.get(ClaimBatch,claim.batch_id))
    if context.batch_id!=claim.batch_id or context.index.actor.organization_id!=actor.organization_id:
        raise PolicyBlocked('NET reference context scope mismatch')
    check=inspect_line(context.index,claim,context.mapping);calc=check['calculation']
    if not calc:return {'reference_check':check,'review_required':True,'findings':[], 'tariff':None,'contract':None}
    if (policy.amount_basis!='NET' or policy.reference_fingerprint!=reference_fingerprint(check)
        or policy.currency!=calc['currency'] or policy.rounding!=calc['rounding'] or policy.precision!=calc['precision']
        or policy.tariff!=Decimal(calc['tariff_unit']) or policy.copay_percent!=Decimal(calc['beneficiary_copay_percent'])):
        raise PolicyBlocked('Signed policy differs from service-date category, network or reference versions')
    differences={x['code'] for x in check['checks'] if x['status']=='difference'}
    review=bool(differences-{'price','copay_amount','net_amount'})
    # A consistent over-tariff invoice may prove a preliminary adjustment.
    # Other mismatches stay for human review, never an automatic deduction.
    if differences and ('price' not in differences or Decimal(calc['source_net'])<Decimal(calc['expected_net'])):review=True
    if differences:
        columns=context.mapping['columns'];raw=claim.source_values
        from mcias.claim_normalization import source_decimal
        if 'copay_amount' in columns:
            stated=source_decimal(raw[columns['copay_amount']])
            expected=money(Decimal(calc['gross'])*policy.copay_percent/100,policy)
            if stated!=expected or Decimal(calc['gross'])-stated!=money(claim.claimed_amount,policy):review=True
    duplicate=db.scalar(select(ClaimEntry.id).where(ClaimEntry.organization_id==claim.organization_id,
        ClaimEntry.id!=claim.id,ClaimEntry.claim_reference==claim.claim_reference,
        ClaimEntry.beneficiary_token==claim.beneficiary_token,ClaimEntry.provider_code==claim.provider_code,
        ClaimEntry.service_code==claim.service_code,ClaimEntry.service_date==claim.service_date).limit(1))
    review=review or bool(duplicate)
    findings=[{'agent':name,'status':('review' if review and name=='duplicates' else 'pass'),
        'reason':('exact_duplicate_or_source_review' if review and name=='duplicates' else 'signed_policy_and_linked_reference_checked'),
        'reference':policy.reference_fingerprint} for name in AGENTS]
    if not check['invoices']:
        next(x for x in findings if x['agent']=='evidence').update(status='hold',reason='missing_invoice')
    return {'reference_check':check,'review_required':review,'findings':findings,
        'tariff':check['references'].get('provider_tariff'),'contract':check['references'].get('contract')}


def decode_policy(data):
    data=dict(data)
    for key in ('copay_percent','tariff','exclusion'):data[key]=Decimal(data[key])
    data['cap']=Decimal(data['cap']) if data.get('cap') is not None else None
    data['order']=tuple(data['order']);policy=AuditPolicy(**data);policy.validate()
    if policy.amount_basis!='NET':raise PolicyBlocked('NET definitions only')
    return policy


def record_definition(db,actor,data):
    if not has_permission(db,actor,'policies.approve'):raise PolicyBlocked('policy approval permission required')
    policy=decode_policy(data);fingerprint=fingerprint_policy(policy)
    verify_registered_policy(db,organization_id=actor.organization_id,policy_fingerprint=fingerprint)
    if db.scalar(select(AuditLog.id).where(AuditLog.organization_id==actor.organization_id,
        AuditLog.action=='policy_definition.recorded',AuditLog.resource_id==fingerprint)):
        return {'fingerprint':fingerprint,'already_recorded':True}
    key,digest=store().put(canonical(policy_definition(policy)))
    source=SourceFile(sha256=digest,storage_key=key,original_filename='signed-policy-definition.json');db.add(source);db.flush()
    db.add(AuditLog(organization_id=actor.organization_id,actor_id=actor.id,action='policy_definition.recorded',
        resource_type='audit_policy_definition',resource_id=fingerprint,details={'source_id':source.id}));db.commit()
    return {'fingerprint':fingerprint,'already_recorded':False}


def definitions(db,actor):
    policies=[]
    for event in db.scalars(select(AuditLog).where(AuditLog.organization_id==actor.organization_id,
        AuditLog.action=='policy_definition.recorded')):
        source=db.get(SourceFile,event.details['source_id'])
        policy=decode_policy(json.loads(store().get(source.storage_key,source.sha256)))
        if fingerprint_policy(policy)!=event.resource_id:raise PolicyBlocked('Policy definition integrity failure')
        policies.append(policy)
    return policies


def requirements(db,actor,batch_id):
    batch=db.get(ClaimBatch,batch_id)
    if not batch or batch.organization_id!=actor.organization_id:raise LookupError('Batch not found')
    context=context_for(db,actor,batch);rows=[]
    for claim in db.scalars(select(ClaimEntry).where(ClaimEntry.batch_id==batch.id).order_by(ClaimEntry.id)):
        check=inspect_line(context.index,claim,context.mapping)
        rows.append({'line_id':claim.id,'reference_fingerprint':reference_fingerprint(check),
            'reference_calculation':check['calculation'],'invoice_present':bool(check['invoices']),
            'requires_signed_policy':True})
    return {'batch_id':batch.id,'items':rows,'financially_final':False}


def execute(db,actor,batch_id):
    if not has_permission(db,actor,'claims.read') or not has_permission(db,actor,'claims.review'):
        raise PolicyBlocked('audit execution permission required')
    batch=db.get(ClaimBatch,batch_id)
    if not batch or batch.organization_id!=actor.organization_id:raise LookupError('Batch not found')
    if batch.status!='imported' or batch.record_count>1000:raise PolicyBlocked('Complete import; execution limit is 1000 lines per batch')
    claims=list(db.scalars(select(ClaimEntry).where(ClaimEntry.batch_id==batch.id).order_by(ClaimEntry.id)))
    if len(claims)!=batch.record_count:raise PolicyBlocked('Batch count mismatch')
    context=context_for(db,actor,batch);policies=[];rows=[]
    for candidate in definitions(db,actor):
        try:verify_registered_policy(db,organization_id=actor.organization_id,policy_fingerprint=fingerprint_policy(candidate))
        except (PolicyBlocked,ValueError):continue
        policies.append(candidate)
    for claim in claims:
        check=inspect_line(context.index,claim,context.mapping)
        row={'line_id':claim.id,'snapshot_id':None,'bucket':'held','reason':'unresolved_reference_or_evidence'}
        if not check['invoices']:row['reason']='missing_invoice'
        elif check['status']=='BLOCKED':pass
        else:
            candidates=[p for p in policies if p.reference_fingerprint==reference_fingerprint(check)]
            if len(candidates)!=1:row['reason']='missing_or_ambiguous_signed_policy'
            else:
                policy=candidates[0]
                try:
                    authorization=verify_registered_policy(db,organization_id=actor.organization_id,policy_fingerprint=fingerprint_policy(policy))
                    snapshot=run_audit(db,actor,claim.id,policy,verified_authorization=authorization,reference_context=context)
                    from mcias.services.result_service import project_line
                    projected=project_line(claim,snapshot)
                    row.update(snapshot_id=snapshot.id,bucket=projected['bucket'],reason=projected['reason'])
                except (PolicyBlocked,ValueError) as exc:
                    row['reason']='policy_or_evidence_blocked';row['detail']=str(exc)
                    if 'review conditions' in str(exc):row.update(bucket='review',reason='reaudit_required')
        rows.append(row)
    dataset={'batch_id':batch.id,'organization_id':actor.organization_id,'source_sha256':batch.source_sha256,
        'rows':rows,'counts':{b:sum(r['bucket']==b for r in rows) for b in ('accepted','rejected','held','review')},
        'total_lines':len(rows),'financially_final':False}
    fingerprint=sha256(canonical(dataset)).hexdigest()
    lock_record(db,'net_audit_manifest',actor.organization_id,batch.id)
    prior=db.scalar(select(AuditLog).where(AuditLog.organization_id==actor.organization_id,
        AuditLog.action=='net_audit.completed',AuditLog.resource_id==batch.id,AuditLog.details['fingerprint'].as_string()==fingerprint))
    if not prior:
        key,digest=store().put(canonical(dataset));source=SourceFile(sha256=digest,storage_key=key,original_filename='net-audit-manifest.json')
        db.add(source);db.flush();db.add(AuditLog(actor_id=actor.id,organization_id=actor.organization_id,
            action='net_audit.completed',resource_type='claim_batch',resource_id=batch.id,
            details={'source_id':source.id,'fingerprint':fingerprint,'total_lines':len(rows)}));db.commit()
    return {**dataset,'fingerprint':fingerprint}


def latest_run(db,actor,batch_id):
    event=db.scalar(select(AuditLog).where(AuditLog.organization_id==actor.organization_id,
        AuditLog.action=='net_audit.completed',AuditLog.resource_id==batch_id).order_by(AuditLog.created_at.desc(),AuditLog.id.desc()).limit(1))
    if not event:return None
    source=db.get(SourceFile,event.details['source_id']);data=json.loads(store().get(source.storage_key,source.sha256))
    if sha256(canonical(data)).hexdigest()!=event.details['fingerprint'] or data['organization_id']!=actor.organization_id:
        raise PolicyBlocked('Audit manifest integrity failure')
    return data
