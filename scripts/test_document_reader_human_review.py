#!/usr/bin/env python3
"""Actual loopback HTTP and Chromium tests. All accounts and sources synthetic."""
import argparse, json, os, sqlite3, subprocess, sys, tempfile, time, uuid
from pathlib import Path
import httpx

def assert_status(fn,status):
    try: fn()
    except httpx.HTTPStatusError as e:
        assert e.response.status_code==status, (e.response.status_code,e.response.text)
        return
    raise AssertionError(f'expected HTTP {status}')

def run(a1,out):
    from playwright.sync_api import sync_playwright
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    port=18767
    with tempfile.TemporaryDirectory(prefix='mcias-human-isolated-') as root:
        app=subprocess.Popen([sys.executable,'scripts/document_reader_human_review_pilot.py','--a1',str(Path(a1).resolve()),
                 '--workdir',root,'--port',str(port)],stdout=(out/'server.log').open('w'),stderr=subprocess.STDOUT,
                 env={**os.environ,'PYTHONPATH':'.:scripts','MCIAS_ENVIRONMENT':'development'})
        client=httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=20)
        try:
            for _ in range(100):
                if app.poll() is not None:raise RuntimeError('server exited: '+(out/'server.log').read_text()[-3000:])
                try:
                    r=client.get('/');
                    if r.status_code==200:break
                except httpx.RequestError:pass
                time.sleep(.5)
            else:raise RuntimeError('server startup timed out')
            r=client.post('/api/login',json={'username':'reviewer-a','password':'demo-reviewer-a-2026'});r.raise_for_status()
            token=r.json()['token'];head={'Authorization':'Bearer '+token}
            r=client.post('/api/login',json={'username':'reviewer-b','password':'demo-reviewer-b-2026'});r.raise_for_status()
            outsider={'Authorization':'Bearer '+r.json()['token']}
            assert_status(lambda:client.get('/api/documents').raise_for_status(),401)
            assert_status(lambda:client.post('/api/login',json={'username':'reviewer-a','password':'bad'}).raise_for_status(),401)
            docs=client.get('/api/documents',headers=head).json();assert len(docs)==3,docs
            by={d['filename'].removesuffix('.pdf'):d['id'] for d in docs}
            assert client.get('/api/documents',headers=outsider).json()==[]
            cases={}
            for name,docid in by.items():
                d=client.get(f'/api/documents/{docid}/evidence',headers=head);d.raise_for_status();items=d.json()
                assert items['status']=='review_required' and len(items['fields'])==18
                assert items['page_count']==(2 if name=='english_columnar' else 1)
                cases[name]=items
                for i in range(1,items['page_count']+1):
                    img=client.get(f'/api/documents/{docid}/pages/{i}',headers=head)
                    assert img.status_code==200 and img.content.startswith(b'\x89PNG')
                assert_status(lambda:client.get(f'/api/documents/{docid}/evidence',headers=outsider).raise_for_status(),404)
                assert_status(lambda:client.get(f'/api/documents/{docid}/pages/1',headers=outsider).raise_for_status(),404)
            assert_status(lambda:client.get(f'/api/documents/{by["english_columnar"]}/pages/3',headers=head).raise_for_status(),404)
            event_ops=[]
            def decide(f,action='accept',version=0,reason='',value=None,op=None,headers=head):
                doc={'action':action,'expected_version':version,'operation_id':op or str(uuid.uuid4()),
                     'reason':reason,'corrected_value':value}
                r=client.post(f'/api/evidence/{f["id"]}/decision',json=doc,headers=headers)
                r.raise_for_status();return r.json(),doc
            # Chromium UI verifies real image overlays, original-cell crop and page navigation.
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1480,'height':980})
                page.goto(f'http://127.0.0.1:{port}/')
                page.locator('#password').fill('demo-reviewer-a-2026')
                page.locator('#login').click()
                page.locator('#evidenceList button').first.wait_for(timeout=20000)
                page.wait_for_function("document.querySelector('#pageImage').naturalWidth>0",timeout=20000)
                assert page.locator('.anchor').count()==18
                assert '1 / 2' in page.locator('#pageNumber').inner_text()
                page.locator('#next').click();assert '2 / 2' in page.locator('#pageNumber').inner_text()
                assert page.locator('.anchor').count()==0
                page.locator('#prev').click()
                page.locator('#evidenceList button').first.click()
                assert page.locator('#cellId').inner_text()
                assert page.locator('#crop').evaluate('(c)=>c.width')==600
                page.locator('#accept').click()
                page.locator('#info').get_by_text('سُجل القرار',exact=False).wait_for(timeout=12000)
                page.screenshot(path=str(out/'review_ui_after_accept.png'),full_page=True)
                browser.close()
            valid_fields=cases['english_columnar']['fields']
            first=valid_fields[0]
            # Accept from browser is exactly one real appended event.
            proof=client.get(f'/api/documents/{by["english_columnar"]}/evidence',headers=head).json()
            assert sum(f['version']==1 for f in proof['fields'])==1
            accepted=next(f for f in proof['fields'] if f['version']==1)
            for f in valid_fields:
                if f['id']!=accepted['id']:decide(f)
            val=client.get(f'/api/documents/{by["english_columnar"]}/a1-preview',headers=head).json()
            assert val['a1_arithmetic_count']==0 and val['financial_decision']=='NOT_AUTHORIZED'
            # B: swapped amounts are transcribed as printed, never auto-corrected.
            for f in cases['english_reordered']['fields']:decide(f)
            swap=client.get(f'/api/documents/{by["english_reordered"]}/a1-preview',headers=head).json()
            assert swap['a1_arithmetic_count']==2 and swap['status']=='HUMAN_REVIEW'
            # C: Arabic uncertain date blocks preview independently of OCR row transcription.
            ar=client.get(f'/api/documents/{by["arabic_rtl"]}/a1-preview',headers=head).json()
            assert ar['status']=='HUMAN_REVIEW' and ar['blocked']
            # Accepted value cannot change without new event; amended version is append-only.
            assert_status(lambda:decide(accepted,'correct',0,'correct a deliberate simulation','42.00'),409)
            assert_status(lambda:decide(accepted,'correct',1,'', '42.00'),422)
            new,_=decide(accepted,'correct',1,'Synthetic deliberate transcription correction for regression','42.00')
            assert new['event']['version']==2 and new['event']['previous_status']=='TRANSCRIPTION_ACCEPTED'
            # Retry same operation = same event, distinct operation with stale version = conflict.
            f=cases['english_reordered']['fields'][0]
            fresh=client.get(f'/api/documents/{by["english_reordered"]}/evidence',headers=head).json()['fields'][0]
            op=str(uuid.uuid4());received,body=decide(f,version=1,reason='Recorded follow-up review amendment',op=op)
            duplicate=client.post(f'/api/evidence/{f["id"]}/decision',json=body,headers=head)
            duplicate.raise_for_status();assert duplicate.json()['idempotent_replay'] is True
            assert duplicate.json()['event']['id']==received['event']['id']
            assert_status(lambda:decide(f,version=1,reason='Conflicting concurrent review on stale version'),409)
            assert_status(lambda:client.post(f'/api/evidence/{f["id"]}/decision',headers=head,
                  json={**body,'action':'reject','reason':'attempt reused operation'}).raise_for_status(),409)
            assert_status(lambda:client.post(f'/api/evidence/{f["id"]}/decision',headers=head,
                  json={**body,'organization_id':'spoofed','expected_version':2}).raise_for_status(),422)
            assert_status(lambda:client.post(f'/api/evidence/{f["id"]}/decision',headers=outsider,
                  json={**body,'expected_version':2,'operation_id':str(uuid.uuid4())}).raise_for_status(),404)
            assert_status(lambda:client.post(f'/api/evidence/{f["id"]}/decision',headers=head,
                  json={**body,'action':'TRUSTED','expected_version':2,'operation_id':str(uuid.uuid4())}).raise_for_status(),422)
            assert_status(lambda:client.post(f'/api/evidence/{f["id"]}/decision',headers=head,
                  json={**body,'action':'approve_payment','expected_version':2,'operation_id':str(uuid.uuid4())}).raise_for_status(),422)
            assert_status(lambda:client.post(f'/api/evidence/{f["id"]}/decision',headers=head,
                  json={**body,'source_sha256':'0'*64,'expected_version':2,'operation_id':str(uuid.uuid4())}).raise_for_status(),422)
            # Reject / unresolved and reason constraints on Arabic source candidate.
            a=cases['arabic_rtl']['fields']
            assert_status(lambda:decide(a[0],'reject',reason='short'),422)
            decide(a[0],'reject',reason='Text not sufficiently readable to attest')
            decide(a[1],'unresolved',reason='Multiple possible readings within OCR region')
            assert client.get(f'/api/documents/{by["arabic_rtl"]}/a1-preview',headers=head).json()['status']=='HUMAN_REVIEW'
            # Reject altered audit trail and altered original candidate table rows (SQLite append-only triggers).
            con=sqlite3.connect(str(Path(root)/'pilot.sqlite3'))
            old_events=con.execute('select count(*) from reader_isolated_review_events').fetchone()[0]
            try:
                for sql in ['update reader_isolated_review_events set new_value="FRAUD" where version=1',
                    'delete from reader_isolated_review_events where version=1',
                    'update reader_ocr_candidate_isolated set observed_value="FRAUD"']:
                    try:con.execute(sql);con.commit()
                    except sqlite3.IntegrityError:con.rollback()
                    else:raise AssertionError('append-only event or original OCR mutation allowed')
            finally:con.close()
            exported=client.get(f'/api/documents/{by["english_columnar"]}/review-export',headers=head).json()
            assert len(exported['reviewed_fields'])==18
            assert exported['financial_decision']=='NOT_AUTHORIZED'
            assert exported['source_attestation']=='NOT_TRUSTED_G2_ROW'
            assert sum(len(row['events']) for row in exported['reviewed_fields'])==19
            # Tampering with encrypted original must fail closed on the live server routes.
            sealed=list((Path(root)/'sealed').iterdir())
            assert len(sealed)==3
            blob=sealed[0].read_bytes();tampered=bytearray(blob);tampered[-1]^=1
            try:
                sealed[0].write_bytes(tampered)
                broken=sum(client.get(f'/api/documents/{d}/pages/1',headers=head).status_code==409 for d in by.values())
                assert broken==1,broken
            finally:sealed[0].write_bytes(blob)
            summary={'status':'ISOLATED_BROWSER_AND_API_REVIEW_TESTED','human_review_real_person':False,
                     'simulated_decisions':old_events,'documents':len(docs),'ui_browser_overlay_fields':18,
                     'pagination_tested':True,'acceptance_18_of_18':True,'swapped_arithmetic_count':2,
                     'arabic_date_hold':True,'append_only_mutation_denied':True,
                     'idempotent_replay':True,'cross_tenant_denied':True,'auth_spoof_denied':True,
                     'original_ciphertext_tamper_denied':True,'a1_trusted_input_used':False,
                     'financial_decision':'NOT_AUTHORIZED'}
            (out/'human_review_results.json').write_text(json.dumps(summary,indent=2))
            print(json.dumps(summary))
        finally:
            client.close();app.terminate()
            try:app.wait(timeout=10)
            except subprocess.TimeoutExpired:app.kill()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--a1',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();run(a.a1,a.out)