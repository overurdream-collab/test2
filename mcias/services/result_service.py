"""Four disjoint preliminary outputs over existing G4/G5 evidence.

This projects existing audit snapshots; it neither audits claims nor invents an
approval. The frozen projection uses the existing encrypted source store and
append-only audit events, keeping the original workbook untouched.
"""
from collections import Counter, defaultdict
from decimal import Decimal
from hashlib import sha256
import json
from uuid import uuid4
from sqlalchemy import select
from mcias.models import AuditLog, SourceFile
from mcias.models_claims import ClaimBatch, ClaimEntry
from mcias.models_audit import AuditSnapshot
from mcias.palermo2 import verify
from mcias.reporting_g7 import amount, number, canonical, ReportBlocked
from mcias.services.registry_service import store
from mcias.services.transaction_lock import lock_record

BUCKETS = ('accepted','rejected','held','review')
LABELS = {'accepted':'مقبول مبدئيًا','rejected':'مرفوض مبدئيًا','held':'معلّق','review':'يحتاج مراجعة'}


def project_line(claim, snapshot):
    item={'line_id':claim.id,'invoice_number':claim.claim_reference,'provider_code':claim.provider_code,
        'service_code':claim.service_code,'service_date':claim.service_date.isoformat(),
        'currency':claim.currency,'claimed_net':number(amount(claim.claimed_amount)),
        'bucket':'held','reason':'not_audited','audited':False,'proposed_net':None,
        'proposed_difference':None,'audit_snapshot_id':snapshot.id if snapshot else None,
        'source_locator':claim.source_locator,'source_record_id':claim.extracted_record_id,
        'source_values':claim.source_values,'financially_final':False}
    if snapshot is None:return item
    if snapshot.organization_id!=claim.organization_id or snapshot.claim_id!=claim.id:
        raise ReportBlocked('Audit evidence scope mismatch')
    item['audited']=True
    findings=snapshot.findings.get('agents',[]) if isinstance(snapshot.findings,dict) else []
    if any(isinstance(f,dict) and f.get('status')=='review' for f in findings):
        return {**item,'bucket':'review','reason':'unresolved_review_finding'}
    calculation=snapshot.calculation
    if not isinstance(calculation,dict) or calculation.get('status')!='calculated':
        return {**item,'reason':'missing_reference_or_evidence'}
    independently=verify(claim,findings,calculation,policy_fingerprint=snapshot.policy_fingerprint,
        policy_id=snapshot.policy_id,reference_check=snapshot.findings.get('reference_check'))
    if independently['status']!='verified' or not isinstance(snapshot.verification,dict) or snapshot.verification.get('status')!='verified':
        return {**item,'bucket':'review','reason':'verification_failed'}
    # Old snapshots do not declare whether copay was already paid. They must
    # not silently become a second copay deduction on the owner's NET input.
    if calculation.get('amount_basis')!='NET':
        return {**item,'bucket':'review','reason':'net_basis_confirmation_required'}
    steps=calculation.get('deductions',[])
    if any(s.get('rule')=='copay' and amount(s.get('deduction'))!=0 for s in steps):
        return {**item,'bucket':'review','reason':'possible_second_copay_deduction'}
    claimed=amount(claim.claimed_amount);payable=amount(calculation['payable'])
    difference=claimed-payable
    return {**item,'bucket':'rejected' if difference>0 else 'accepted',
        'reason':'proven_financial_difference' if difference>0 else 'verified_match',
        'proposed_net':number(payable),'proposed_difference':number(difference)}


def partition(rows, expected_ids):
    ids=[row['line_id'] for row in rows]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected_ids):
        raise ReportBlocked('Missing or duplicate claim line in output partition')
    if any(row['bucket'] not in BUCKETS for row in rows):
        raise ReportBlocked('Unknown output category')
    counts=Counter(row['bucket'] for row in rows)
    totals=defaultdict(lambda:{key:Decimal(0) for key in BUCKETS})
    for row in rows:totals[row['currency']][row['bucket']]+=amount(row['claimed_net'])
    return {'total_lines':len(rows),'counts':{key:counts[key] for key in BUCKETS},
        'claimed_net_by_currency':{currency:{key:number(value) for key,value in values.items()} for currency,values in sorted(totals.items())},
        'unique_line_count':len(set(ids)),'financially_final':False}


def _events(db,org):
    return select(AuditLog).where(AuditLog.organization_id==org,
        AuditLog.action=='result_set.created',AuditLog.resource_type=='audit_result_set')


def freeze(db,actor,batch_id):
    from mcias.services.rbac_service import _atomic
    with _atomic(db):
        lock_record(db,'result_set',actor.organization_id,batch_id)
        batch=db.get(ClaimBatch,batch_id)
        if not batch or batch.organization_id!=actor.organization_id:raise LookupError('Batch not found')
        if batch.status!='imported' or batch.record_count!=batch.imported_count:
            raise ReportBlocked('Complete the batch import before creating outputs')
        claims=list(db.scalars(select(ClaimEntry).where(ClaimEntry.batch_id==batch.id,
            ClaimEntry.organization_id==actor.organization_id).order_by(ClaimEntry.id)))
        if len(claims)!=batch.record_count or len(claims)>10000:
            raise ReportBlocked('Batch count mismatch or output limit exceeded')
        snapshots={}
        for row in db.scalars(select(AuditSnapshot).join(ClaimEntry,ClaimEntry.id==AuditSnapshot.claim_id).where(
            ClaimEntry.batch_id==batch.id,AuditSnapshot.organization_id==actor.organization_id).order_by(AuditSnapshot.created_at,AuditSnapshot.id)):
            snapshots[row.claim_id]=row
        rows=[project_line(claim,snapshots.get(claim.id)) for claim in claims]
        from mcias.services.net_audit_service import latest_run
        run=latest_run(db,actor,batch.id)
        outcomes={r['line_id']:r for r in run['rows']} if run else {}
        for row in rows:
            outcome=outcomes.get(row['line_id'])
            if outcome and outcome['bucket'] in ('held','review'):
                row.update(bucket=outcome['bucket'],reason=outcome['reason'],proposed_net=None,proposed_difference=None)
        from mcias.services.invoice_service import invoices
        for claim,row in zip(claims,rows):
            evidence=invoices(db,claim);row['invoices']=evidence
            if not evidence:
                row.update(bucket='held',reason='missing_invoice',reason_ar='نقص المرفقات — فاتورة الخدمة غير متوفرة',
                    audited=False,proposed_net=None,proposed_difference=None)
            else:
                snapshot=snapshots.get(claim.id)
                calculation=snapshot.calculation if snapshot else None
                if isinstance(calculation,dict) and calculation.get('amount_basis')=='NET' and calculation.get('invoice_evidence')!=evidence:
                    row.update(bucket='review',reason='invoice_evidence_changed_reaudit_required',
                        reason_ar='تغيرت أدلة الفاتورة بعد التدقيق — يلزم إعادة تدقيق معتمدة',
                        proposed_net=None,proposed_difference=None)
        summary=partition(rows,[claim.id for claim in claims])
        dataset={'schema':'mcias-four-results-v1','batch_id':batch.id,'organization_id':actor.organization_id,
            'source_sha256':batch.source_sha256,'stage':'preliminary','rows':rows,'summary':summary}
        digest=sha256(canonical(dataset)).hexdigest()
        previous=db.scalar(_events(db,actor.organization_id).where(AuditLog.details['fingerprint'].as_string()==digest).limit(1))
        if previous:return public(previous)
        object_id,stored_digest=store().put(canonical(dataset))
        source=SourceFile(sha256=stored_digest,original_filename='frozen-preliminary-results.json',storage_key=object_id)
        db.add(source);db.flush()
        event=AuditLog(actor_id=actor.id,organization_id=actor.organization_id,action='result_set.created',
            resource_type='audit_result_set',resource_id=str(uuid4()),category='reporting',details={
                'source_id':source.id,'fingerprint':digest,'batch_id':batch.id,'summary':summary})
        db.add(event);db.flush();return public(event)


def public(event):
    return {'id':event.resource_id,'batch_id':event.details['batch_id'],'fingerprint':event.details['fingerprint'],
        'summary':event.details['summary'],'created_at':event.created_at,'stage':'preliminary','financially_final':False}


def list_results(db,actor,offset=0,limit=25):
    events=list(db.scalars(_events(db,actor.organization_id).order_by(AuditLog.created_at.desc(),AuditLog.id).offset(offset).limit(limit+1)))
    return {'items':[public(e) for e in events[:limit]],'has_more':len(events)>limit,'offset':offset,'limit':limit}


def read(db,actor,result_id):
    event=db.scalar(_events(db,actor.organization_id).where(AuditLog.resource_id==result_id))
    if not event:raise LookupError('Result set not found')
    source=db.get(SourceFile,event.details['source_id'])
    if not source:raise ReportBlocked('Frozen results source missing')
    raw=store().get(source.storage_key,source.sha256)
    dataset=json.loads(raw)
    if sha256(canonical(dataset)).hexdigest()!=event.details['fingerprint'] or dataset['organization_id']!=actor.organization_id:
        raise ReportBlocked('Frozen output integrity failure')
    summary=partition(dataset['rows'],[row['line_id'] for row in dataset['rows']])
    if summary!=dataset['summary'] or summary!=event.details['summary']:
        raise ReportBlocked('Frozen output summary mismatch')
    return dataset
