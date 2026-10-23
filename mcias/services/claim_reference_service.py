"""Pre-audit reference validation over the existing encrypted input registry.

No new audit engine, approvals or SQL reference tables. This resolves explicit
links at service date and compares NET source amounts using contract rounding.
Passing these checks is not a completed audit or a binding financial decision.
"""
from collections import Counter
from datetime import date
from decimal import Decimal
from hashlib import sha256
import json
from types import SimpleNamespace
from sqlalchemy import select
from mcias.models import AuditLog, SourceFile
from mcias.models_claims import ClaimBatch, ClaimEntry
from mcias.audit_engine import money
from mcias.claim_batches import confirmed_mapping
from mcias.claim_normalization import source_decimal
from mcias.reporting_g7 import canonical
from mcias.schemas.reference_links import PROVIDERS
from mcias.services import registry_service as registry
from mcias.services.rbac_service import _atomic
from mcias.services.transaction_lock import lock_record


class ReferenceCheckConflict(ValueError):
    pass


def _text(value):
    return ' '.join(str(value).split())


class ReferenceIndex:
    def __init__(self, db, actor):
        self.db,self.actor,self.cache=db,actor,{}

    def at(self, feature, at):
        key=(feature,at)
        if key not in self.cache:
            self.cache[key]=[r for r in registry.effective_records(self.db,self.actor,feature,at) if not r.get('parent_id')]
        return self.cache[key]

    def linked(self, feature, identity, at):
        return next((r for r in self.at(feature,at) if r['id']==identity),None)


def _number(value, *, allow_percent=False):
    return source_decimal(value,allow_percent=allow_percent)


def inspect_line(index, claim, mapping):
    checks=[];references={}
    from mcias.services.invoice_service import invoices
    invoice_evidence=invoices(index.db,claim)
    checks.append({'code':'invoice','status':'pass' if invoice_evidence else 'hold',
        'reason':'operator_linked_invoice' if invoice_evidence else 'missing_invoice'})
    def check(code,state,**values):
        checks.append({'code':code,'status':state,**values})
    def remember(role,row):
        if row:references[role]={'id':row['id'],'version':row['version'],'event_id':row['event_id'],
            'source_sha256':row['source_sha256'],'effective_from':row['effective_from'],'effective_to':row['effective_to']}
        return row
    def one(code,rows):
        row=rows[0] if len(rows)==1 else None
        check(code,'pass' if row else 'hold',reason='unique_effective_reference' if row else ('ambiguous_reference' if rows else 'missing_effective_reference'))
        return remember(code,row)
    def finish(calculation=None):
        states={c['status'] for c in checks}
        status='BLOCKED' if 'hold' in states else ('REVIEW_REQUIRED' if 'difference' in states else 'MATCHED')
        return {'line_id':claim.id,'status':status,'checks':checks,'references':references,
            'calculation':calculation,'invoices':invoice_evidence,'source_columns':dict(mapping.get('columns',{})) if mapping else {},
            'stage':'reference_validation','audit_completed':False,'financially_final':False}

    day=claim.service_date
    beneficiary=one('beneficiary_enrollment',[r for r in index.at('beneficiaries.names',day)
        if r['values']['beneficiary_token']==claim.beneficiary_token])
    columns=mapping.get('columns',{}) if mapping else {}
    raw=claim.source_values
    def source(key):
        return raw.get(columns[key]) if key in columns else None
    category=None
    if beneficiary:
        category=one('category',[r for r in index.at('beneficiaries.categories',day)
            if r['id']==beneficiary.get('links',{}).get('category') and r['values']['category_code']==beneficiary['values']['category_code']])
        if source('beneficiary_name') is not None:
            check('beneficiary_name','pass' if _text(source('beneficiary_name'))==_text(beneficiary['title']) else 'difference')
        else:check('beneficiary_name','hold',reason='confirm_beneficiary_name_column')
        if source('category_code') is not None and category:
            check('source_category','pass' if _text(source('category_code'))==category['values']['category_code'] else 'difference')
    providers=[r for section in PROVIDERS for r in index.at(section,day)
        if _text(claim.provider_code) in (_text(r['values']['provider_code']),_text(r['title']))]
    provider=one('provider',providers)
    service=one('service',[r for r in index.at('providers.services',day)
        if _text(claim.service_code) in (_text(r['values']['service_code']),_text(r['title']))])
    price=None;contract=None;regulation=None;rate=None
    if provider and service:
        price=one('provider_tariff',[r for r in index.at('providers.prices',day)
            if r.get('links',{}).get('provider')==provider['id'] and r.get('links',{}).get('service')==service['id']
            and r['values']['provider_code']==provider['values']['provider_code']
            and r['values']['service_code']==service['values']['service_code']])
    if price:
        contract=one('contract',[r for r in index.at('inputs.contracts',day)
            if r['id']==price.get('links',{}).get('contract') and r.get('links',{}).get('provider')==provider['id']
            and r['values']['provider_code']==provider['values']['provider_code']])
    if contract:
        regulation=one('regulation',[r for r in index.at('inputs.regulations',day)
            if r.get('links',{}).get('contract')==contract['id']])
        if category and service:
            rate=one('copay_rule',[r for r in index.at('beneficiaries.cost_sharing',day)
                if r.get('links',{}).get('category')==category['id'] and r.get('links',{}).get('contract')==contract['id']
                and r['values']['category_code']==category['values']['category_code']
                and r.get('terms',{}).get('service_type')==service.get('terms',{}).get('service_type')
                and r.get('terms',{}).get('network')==contract.get('terms',{}).get('network')])
    if not all((beneficiary,category,provider,service,price,contract,regulation,rate)):
        return finish()
    terms=contract.get('terms',{})
    if (not mapping or mapping.get('amount_basis')!='NET'
            or regulation.get('terms',{}).get('amount_basis')!='NET'
            or regulation.get('terms',{}).get('unit_basis')!='ONE_SERVICE_PER_ROW'
            or terms.get('precision') not in (0,2,4) or terms.get('rounding') not in ('HALF_UP','HALF_EVEN')):
        check('financial_basis','hold',reason='explicit_net_basis_and_rounding_required');return finish()
    if claim.currency!=terms.get('currency') or claim.currency!=price['values']['currency']:
        check('currency','hold',reason='currency_mismatch_no_conversion');return finish()
    policy=SimpleNamespace(precision=terms['precision'],rounding=terms['rounding'])
    try:
        quantity=_number(source('quantity')) if source('quantity') is not None else Decimal(1)
        if quantity<=0:raise ReferenceCheckConflict('Quantity must be positive')
        unit=_number(source('unit_price')) if source('unit_price') is not None else None
        gross=_number(source('gross_amount')) if source('gross_amount') is not None else (unit*quantity if unit is not None else None)
        if gross is None:
            check('gross_amount','hold',reason='confirm_gross_or_unit_price_column');return finish()
        gross=money(gross,policy);net=money(claim.claimed_amount,policy)
        tariff=money(Decimal(price['values']['amount'])*quantity,policy)
        percent=Decimal(rate['values']['percent'])
        if not Decimal(0)<=percent<=Decimal(100):raise ReferenceCheckConflict('Invalid reference percentage')
        base=min(gross,tariff)
        expected_copay=money(base*percent/Decimal(100),policy)
        expected_net=money(base-expected_copay,policy)
        check('price','pass' if gross<=tariff else 'difference',source_gross=str(gross),tariff_total=str(tariff))
        if unit is not None:
            check('gross_total','pass' if money(unit*quantity,policy)==gross else 'difference')
        if source('copay_percent') is not None:
            observed_percent=_number(source('copay_percent'),allow_percent=True)
            check('copay_percent','pass' if observed_percent==percent else 'difference',expected=str(percent),source=str(observed_percent))
        if source('copay_amount') is not None:
            observed_copay=money(_number(source('copay_amount')),policy)
            check('copay_amount','pass' if observed_copay==expected_copay else 'difference',expected=str(expected_copay),source=str(observed_copay))
            check('source_arithmetic','pass' if gross-observed_copay==net else 'difference')
        else:
            check('implied_copay','pass' if gross-net==expected_copay else 'difference',expected=str(expected_copay),source=str(gross-net))
        if source('total_amount') is not None:
            check('source_net_total','pass' if money(_number(source('total_amount')),policy)==net else 'difference')
        check('net_amount','pass' if net==expected_net else 'difference',expected=str(expected_net),source=str(net))
        return finish({'category_code':category['values']['category_code'],'service_type':service['terms']['service_type'],
            'network':terms['network'],'currency':claim.currency,'quantity':str(quantity),'gross':str(gross),
            'tariff_unit':price['values']['amount'],'beneficiary_copay_percent':str(percent),
            'expected_copay':str(expected_copay),'expected_net':str(expected_net),'source_net':str(net),
            'net_difference':str(net-expected_net),'amount_basis':'NET','copay_deducted_again':False,
            'rounding':terms['rounding'],'precision':terms['precision']})
    except (ValueError,ArithmeticError):
        check('source_numbers','hold',reason='invalid_source_amount_or_quantity');return finish()


def _events(org,batch_id):
    return select(AuditLog).where(AuditLog.organization_id==org,AuditLog.action=='claim_references.checked',
        AuditLog.resource_type=='claim_batch',AuditLog.resource_id==batch_id)


def _public(event):
    return {'id':event.id,'batch_id':event.resource_id,'summary':event.details['summary'],
        'fingerprint':event.details['fingerprint'],'created_at':event.created_at,
        'stage':'reference_validation','audit_completed':False,'financially_final':False}


def run(db,actor,batch_id):
    with _atomic(db):
        lock_record(db,'reference_check',actor.organization_id,batch_id)
        batch=db.get(ClaimBatch,batch_id)
        if not batch or batch.organization_id!=actor.organization_id:raise LookupError('Batch not found')
        if batch.status!='imported' or batch.record_count!=batch.imported_count:
            raise ReferenceCheckConflict('Complete the import before reference validation')
        claims=list(db.scalars(select(ClaimEntry).where(ClaimEntry.batch_id==batch.id,
            ClaimEntry.organization_id==actor.organization_id).order_by(ClaimEntry.id)))
        if len(claims)!=batch.record_count or len(claims)>10000:raise ReferenceCheckConflict('Batch count or limit mismatch')
        mapping=confirmed_mapping(db,batch);index=ReferenceIndex(db,actor)
        rows=[inspect_line(index,claim,mapping) for claim in claims]
        counts=Counter(r['status'] for r in rows)
        summary={'total_lines':len(rows),**{key:counts[key] for key in ('MATCHED','REVIEW_REQUIRED','BLOCKED')}}
        dataset={'schema':'mcias-linked-reference-check-v1','organization_id':actor.organization_id,
            'batch_id':batch.id,'source_sha256':batch.source_sha256,'rows':rows,'summary':summary,
            'stage':'reference_validation','audit_completed':False,'financially_final':False}
        fingerprint=sha256(canonical(dataset)).hexdigest()
        existing=db.scalar(_events(actor.organization_id,batch.id).where(AuditLog.details['fingerprint'].as_string()==fingerprint).limit(1))
        if existing:return _public(existing)
        object_id,digest=registry.store().put(canonical(dataset))
        source=SourceFile(sha256=digest,storage_key=object_id,original_filename='claim-reference-validation.json')
        db.add(source);db.flush()
        event=AuditLog(actor_id=actor.id,organization_id=actor.organization_id,action='claim_references.checked',
            resource_type='claim_batch',resource_id=batch.id,category='reference_validation',
            details={'source_id':source.id,'fingerprint':fingerprint,'summary':summary})
        db.add(event);db.flush();return _public(event)


def read(db,actor,batch_id):
    event=db.scalar(_events(actor.organization_id,batch_id).order_by(AuditLog.created_at.desc(),AuditLog.id.desc()).limit(1))
    if not event:raise LookupError('Reference validation not found')
    source=db.get(SourceFile,event.details['source_id'])
    if source is None:raise ReferenceCheckConflict('Reference validation source missing')
    dataset=json.loads(registry.store().get(source.storage_key,source.sha256))
    if (dataset['organization_id']!=actor.organization_id or dataset['batch_id']!=batch_id
            or sha256(canonical(dataset)).hexdigest()!=event.details['fingerprint']):
        raise ReferenceCheckConflict('Reference validation integrity failure')
    return {**dataset,'id':event.id,'fingerprint':event.details['fingerprint'],'created_at':event.created_at}
