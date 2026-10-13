"""Intake is real, encrypted and nonbinding; fixtures never activate financial rules."""
from datetime import date
import io,json
from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from mcias.models import AuditLog, SourceFile, User
from mcias.schemas.registry import SCHEMAS, validate_values
from mcias.services import feature_service as f

@pytest.fixture
def registry(features_api,monkeypatch,tmp_path):
    a=features_api
    monkeypatch.setenv('MCIAS_STORAGE_DIR',str(tmp_path/'encrypted'))
    monkeypatch.setenv('MCIAS_STORAGE_KEY','11'*32)
    monkeypatch.setenv('MCIAS_ENVIRONMENT','development')
    return a,tmp_path

def data(feature,code='SYN-ONE'):
    values={key:'SYN-value' for key in SCHEMAS[feature]}
    values['record_code']=code
    for key,value in [('currency','LYD'),('amount','100.0000'),('percent','10'),('coding_system','LOCAL')]:
        if key in values:values[key]=value
    return {'title':'اسم اصطناعي خاص','effective_from':date.today().isoformat(),'values':values}

def enable(a,feature):
    with Session(a.engine) as db:f.grant_feature(db,a.organization_id,feature,a.ids['root']);db.commit()

@pytest.mark.parametrize('feature',list(SCHEMAS))
def test_all_sixteen_sections_create_read_close_version_and_history(registry,feature):
    a,tmp=registry;enable(a,feature);base='/api/v1/registry/'+feature
    created=a.client.post(base+'/records',json=data(feature),headers=a.headers['admin'])
    assert created.status_code==201,created.text
    row=created.json();assert row['status']=='open' and row['financially_active'] is False
    assert a.client.get(base+'/records?q=اصطناعي',headers=a.headers['admin']).json()['total']==1
    assert a.client.get(base+'/records/'+row['id'],headers=a.headers['other']).status_code==403
    assert a.client.post(base+'/records/'+row['id']+'/close',headers=a.headers['admin'],json={'reason':'اختبار الإغلاق','expected_version':1}).status_code==200
    closed=a.client.get(base+'/records/'+row['id'],headers=a.headers['admin']).json()
    assert closed['status']=='closed' and closed['close_reason']=='اختبار الإغلاق'
    assert a.client.post(base+'/records/'+row['id']+'/close',headers=a.headers['admin'],json={'reason':'again','expected_version':1}).status_code==409
    assert a.client.post(base+'/records/'+row['id']+'/versions',headers=a.headers['admin'],json={**data(feature),'expected_version':2}).status_code==201
    history=a.client.get(base+'/records/'+row['id']+'/history',headers=a.headers['admin']).json()['items']
    assert [r['version'] for r in history]==[1,2,3]
    assert history[0]['status']=='open' and history[1]['status']=='closed'
    with Session(a.engine) as db:
        events=list(db.scalars(select(AuditLog).where(AuditLog.category=='reference_intake')))
        assert 'اسم اصطناعي خاص' not in json.dumps([e.details for e in events],ensure_ascii=False)
        assert all('values' not in e.details for e in events)
    assert all('اسم اصطناعي خاص'.encode() not in p.read_bytes() for p in (tmp/'encrypted').iterdir())

def test_no_entitlement_or_permission_and_sanitized_validation(registry):
    a,_=registry;base='/api/v1/registry/beneficiaries.names'
    assert a.client.post(base+'/records',json=data('beneficiaries.names'),headers=a.headers['admin']).status_code==403
    enable(a,'beneficiaries.names')
    assert a.client.get(base+'/records',headers=a.headers['viewer']).status_code==403
    secret='PRIVATE-invalid-value'
    response=a.client.post(base+'/records',json={**data('beneficiaries.names'),'effective_from':secret},headers=a.headers['admin'])
    assert response.status_code==422 and secret not in response.text
    assert a.client.post(base+'/records',json={**data('beneficiaries.names'),'status':'approved'},headers=a.headers['admin']).status_code==422

@pytest.mark.parametrize('feature,key,bad',[('inputs.caps','amount','NaN'),('inputs.caps','amount','-1'),
    ('providers.prices','currency','lyd'),('beneficiaries.cost_sharing','percent','101'),('providers.services','coding_system','SQL')])
def test_values_are_strict(feature,key,bad):
    values=data(feature)['values'];values[key]=bad
    with pytest.raises(ValueError):validate_values(feature,values)

@pytest.mark.parametrize('kind',['csv','xlsx'])
def test_file_preview_commit_idempotency_and_linked_evidence(registry,kind):
    a,_=registry;feature='providers.hospitals';enable(a,feature);base='/api/v1/registry/'+feature
    headers=['title','effective_from',*SCHEMAS[feature]]
    cells=['SYN-Hospital',date.today().isoformat(),'SYN-HOSPITAL','SYN-PROVIDER']
    if kind=='csv':raw=(','.join(headers)+'\n'+','.join(cells)+'\n').encode()
    else:
        workbook=Workbook();workbook.active.append(headers);workbook.active.append(cells)
        stream=io.BytesIO();workbook.save(stream);raw=stream.getvalue()
    upload=a.client.post(base+'/imports?filename=SYN-source.'+kind,content=raw,headers={**a.headers['admin'],'Content-Type':'application/octet-stream'})
    assert upload.status_code==201,upload.text
    doc=upload.json()['document_id']
    preview=a.client.get(base+'/imports/'+doc+'/preview',headers=a.headers['admin']).json()
    assert len(preview['items'])==1 and preview['items'][0]['valid']
    body={'record_ids':[preview['items'][0]['id']]}
    commit=a.client.post(base+'/imports/'+doc+'/commit',json=body,headers=a.headers['admin'])
    assert commit.status_code==201,commit.text
    row=commit.json()['items'][0]
    evidence=base+'/records/'+row['id']+'/evidence/'+doc
    assert a.client.get(evidence,headers=a.headers['admin']).content==raw
    assert a.client.get(evidence,headers=a.headers['other']).status_code==403
    assert a.client.post(base+'/imports/'+doc+'/commit',json=body,headers=a.headers['admin']).status_code==409

def test_pdf_requires_human_mapping_and_preserves_source(registry):
    a,_=registry;feature='inputs.contracts';enable(a,feature);base='/api/v1/registry/'+feature
    stream=io.BytesIO();pdf=canvas.Canvas(stream);pdf.drawString(40,700,'SYN contract evidence only');pdf.save();raw=stream.getvalue()
    upload=a.client.post(base+'/imports?filename=SYN-contract.pdf',content=raw,headers=a.headers['admin'])
    assert upload.status_code==201,upload.text
    doc=upload.json()['document_id']
    preview=a.client.get(base+'/imports/'+doc+'/preview',headers=a.headers['admin']).json()
    assert preview['items'][0]['manual_required'] and not preview['items'][0]['valid']
    commit=a.client.post(base+'/imports/'+doc+'/commit',json={'manual_record':data(feature)},headers=a.headers['admin'])
    assert commit.status_code==201 and commit.json()['items'][0]['evidence']['document_id']==doc

def test_duplicate_and_stale_creation_roll_back(registry):
    a,_=registry;feature='providers.labs';enable(a,feature);base='/api/v1/registry/'+feature
    assert a.client.post(base+'/records',json=data(feature),headers=a.headers['admin']).status_code==201
    assert a.client.post(base+'/records',json=data(feature),headers=a.headers['admin']).status_code==409
    assert a.client.get(base+'/records',headers=a.headers['admin']).json()['total']==1
    with Session(a.engine) as db:f.revoke_feature(db,a.organization_id,feature,a.ids['root'],'Revocation');db.commit()
    assert a.client.get(base+'/records',headers=a.headers['admin']).status_code==403
