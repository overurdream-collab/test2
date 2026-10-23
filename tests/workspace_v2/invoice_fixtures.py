"""Upload actual synthetic PDF pages and explicitly link every service line."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from mcias.models_claims import ClaimEntry
from mcias.seed.synthetic_invoices import invoice_pdf

def attach_invoices(api,batch,skip_ids=()):
    with Session(api.engine) as db:
        claims=list(db.scalars(select(ClaimEntry).where(ClaimEntry.batch_id==batch).order_by(ClaimEntry.id)))
        rows=[{'invoice_reference':c.claim_reference,'beneficiary':c.beneficiary_token,'provider':c.provider_code,
            'service':c.service_code,'service_date':c.service_date.isoformat(),
            'gross':c.source_values.get('المطلوب',str(c.claimed_amount)),
            'copay':c.source_values.get('إجمالي التحمل','0'),'net':str(c.claimed_amount),'currency':c.currency} for c in claims]
        ids=[c.id for c in claims if c.id not in skip_ids]
    raw=invoice_pdf(rows)
    response=api.client.post('/api/v1/ingestion/uploads?filename=SYN-invoice-bundle.pdf',content=raw,
        headers={**api.headers['root'],'Content-Type':'application/octet-stream'})
    assert response.status_code==200 and response.json()['status'] in ('extracted','duplicate'),response.text
    document=response.json()['document_id']
    for identity in ids:
        linked=api.client.post(f'/api/v1/claims/entries/{identity}/attachments/{document}?kind=invoice',headers=api.headers['root'])
        assert linked.status_code==201,linked.text
    return document,raw
