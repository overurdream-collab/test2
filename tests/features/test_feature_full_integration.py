"""A single authenticated grant -> intake/import -> revocation -> regrant cycle."""
from datetime import date
import os
import pytest

@pytest.mark.parametrize('postgres',[False,True])
def test_complete_feature_and_intake_cycle(api_factory,features_api,monkeypatch,tmp_path,postgres):
    if postgres:
        url=os.getenv('MCIAS_RBAC_API_DATABASE_URL')
        if not url:pytest.skip('isolated PostgreSQL API URL required')
        a=api_factory(url=url)
    else:a=features_api
    monkeypatch.setenv('MCIAS_STORAGE_DIR',str(tmp_path/'encrypted'))
    monkeypatch.setenv('MCIAS_STORAGE_KEY','11'*32)
    base=f'/api/v1/organizations/{a.organization_id}/features';feature='providers.hospitals'
    intake='/api/v1/registry/'+feature
    assert a.client.get('/api/v1/me/features',headers=a.headers['admin']).json()['features']==[]
    assert a.client.post(base+'/'+feature+'/grant',headers=a.headers['admin']).status_code==403
    assert a.client.post(base+'/'+feature+'/grant',headers=a.headers['root']).status_code==201
    assert a.client.get('/api/v1/me/features',headers=a.headers['admin']).json()['features']==[feature]
    raw=('title,effective_from,record_code,provider_code\nSYN Hospital,'+date.today().isoformat()+',SYN-CYCLE,SYN-PROVIDER\n').encode()
    upload=a.client.post(intake+'/imports?filename=SYN-cycle.csv',content=raw,headers=a.headers['admin'])
    assert upload.status_code==201,upload.text
    document=upload.json()['document_id']
    preview=a.client.get(intake+'/imports/'+document+'/preview',headers=a.headers['admin']).json()
    assert preview['items'][0]['valid']
    commit=a.client.post(intake+'/imports/'+document+'/commit',headers=a.headers['admin'],json={'record_ids':[preview['items'][0]['id']]})
    assert commit.status_code==201,commit.text
    record=commit.json()['items'][0]
    assert record['financially_active'] is False
    evidence=intake+'/records/'+record['id']+'/evidence/'+document
    assert a.client.get(evidence,headers=a.headers['admin']).content==raw
    assert a.client.get(evidence,headers=a.headers['other']).status_code==403
    assert a.client.post(base+'/'+feature+'/revoke',headers=a.headers['root'],json={'reason':'Synthetic cycle completed'}).status_code==200
    assert a.client.get('/api/v1/me/features',headers=a.headers['admin']).json()['features']==[]
    assert a.client.get(evidence,headers=a.headers['admin']).status_code==403
    assert a.client.post(base+'/'+feature+'/grant',headers=a.headers['root']).status_code==201
    assert a.client.get(evidence,headers=a.headers['admin']).content==raw
    assert a.client.get(intake+'/records',headers=a.headers['admin']).json()['total']==1
