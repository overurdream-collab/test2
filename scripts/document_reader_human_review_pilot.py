#!/usr/bin/env python3
"""ISOLATED synthetic G2 OCR human attestation demo. No production exposure.

Reuses existing EncryptedStore, G2 ORM and Reader OCR fixtures; append-only local
review decisions never upgrade G2 ingestion or A1 source-verification authority.
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, secrets, tempfile, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel as Schema, ConfigDict, Field
from sqlalchemy import create_engine, select, ForeignKey, Integer, String, JSON, UniqueConstraint, text
from sqlalchemy.orm import Session, Mapped, mapped_column
import fitz
from mcias.models import Base, Organization, User, SourceFile, uid
from mcias.models_ingestion import IngestionDocument, IngestionJob, ExtractedSourceRecord
from mcias.ingestion.orchestrator import ingest
from mcias.storage import EncryptedStore
from document_reader_dynamic_layout_pilot import STYLES, make_fixture, read_pixels_and_words, parse_dynamic, a1_payload, load_a1
from g2_trust_pilot import reopen
from g2_ocr_evidence_qualification_pilot import Candidate, create_candidates, all_candidates, FIELDS

STATES=('UNVERIFIED_OCR_CANDIDATE','PENDING_HUMAN_REVIEW','TRANSCRIPTION_ACCEPTED',
        'TRANSCRIPTION_CORRECTED','REJECTED','UNRESOLVED')
FINAL={'TRANSCRIPTION_ACCEPTED','TRANSCRIPTION_CORRECTED'}

class EvidenceSeal(Base):
    __tablename__='reader_isolated_evidence_seal'
    candidate_id: Mapped[str]=mapped_column(ForeignKey('reader_ocr_candidate_isolated.id'),primary_key=True)
    evidence_sha256: Mapped[str]=mapped_column(String(64),nullable=False)

class ReviewEvent(Base):
    __tablename__='reader_isolated_review_events'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id: Mapped[str]=mapped_column(ForeignKey('organizations.id'),nullable=False)
    document_id: Mapped[str]=mapped_column(ForeignKey('ingestion_documents.id'),nullable=False)
    candidate_id: Mapped[str]=mapped_column(ForeignKey('reader_ocr_candidate_isolated.id'),nullable=False)
    source_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    page: Mapped[int]=mapped_column(Integer,nullable=False)
    bbox: Mapped[list]=mapped_column(JSON,nullable=False)
    observed_value: Mapped[str]=mapped_column(String(300),nullable=False)
    previous_status: Mapped[str]=mapped_column(String(48),nullable=False)
    new_status: Mapped[str]=mapped_column(String(48),nullable=False)
    new_value: Mapped[str|None]=mapped_column(String(300))
    reason: Mapped[str]=mapped_column(String(800),nullable=False)
    reviewer_id: Mapped[str]=mapped_column(ForeignKey('users.id'),nullable=False)
    timestamp: Mapped[str]=mapped_column(String(40),nullable=False)
    version: Mapped[int]=mapped_column(Integer,nullable=False)
    operation_id: Mapped[str]=mapped_column(String(96),nullable=False)
    request_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    previous_event_hash: Mapped[str]=mapped_column(String(64),nullable=False)
    event_hash: Mapped[str]=mapped_column(String(64),nullable=False)
    __table_args__=(UniqueConstraint('candidate_id','version'),UniqueConstraint('candidate_id','operation_id'))

class Decision(Schema):
    model_config=ConfigDict(extra='forbid',strict=True)
    action: Literal['pending','accept','correct','reject','unresolved']
    expected_version: int=Field(ge=0)
    operation_id: str=Field(min_length=8,max_length=96)
    corrected_value: str|None=Field(default=None,max_length=300)
    reason: str=Field(default='',max_length=800)

MAPPING={'pending':'PENDING_HUMAN_REVIEW','accept':'TRANSCRIPTION_ACCEPTED',
         'correct':'TRANSCRIPTION_CORRECTED','reject':'REJECTED','unresolved':'UNRESOLVED'}

def digest_json(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def fingerprint(c):
    return digest_json({'tenant':c.organization_id,'doc':c.document_id,'job':c.job_id,
        'sha':c.source_sha256,'page':c.page,'row':c.row_id,'field':c.field_name,
        'ocr':c.observed_value,'bbox':c.bbox,'words':c.ocr_words,'conf':c.ocr_confidence,
        'status':c.status})

def events(db,cid):
    return db.scalars(select(ReviewEvent).where(ReviewEvent.candidate_id==cid)
                      .order_by(ReviewEvent.version)).all()

def verify_history(db,c):
    seal=db.get(EvidenceSeal,c.id)
    if seal is None or seal.evidence_sha256!=fingerprint(c) or c.status!='UNVERIFIED_OCR_CANDIDATE':
        raise HTTPException(409,'ORIGINAL_OCR_EVIDENCE_CHANGED')
    chain='0'*64; all_events=events(db,c.id)
    for ix,e in enumerate(all_events,1):
        fields={'candidate_id':e.candidate_id,'organization_id':e.organization_id,
            'document_id':e.document_id,'source_sha256':e.source_sha256,
            'page':e.page,'bbox':e.bbox,'observed_value':e.observed_value,
            'previous_status':e.previous_status,'new_status':e.new_status,
            'new_value':e.new_value,'reason':e.reason,'reviewer_id':e.reviewer_id,
            'timestamp':e.timestamp,'version':e.version,'operation_id':e.operation_id,
            'request_sha256':e.request_sha256,'previous_event_hash':e.previous_event_hash}
        if (e.version!=ix or e.previous_event_hash!=chain or e.event_hash!=digest_json(fields)
            or e.source_sha256!=c.source_sha256 or e.document_id!=c.document_id
            or e.organization_id!=c.organization_id or e.bbox!=c.bbox or e.page!=c.page
            or e.observed_value!=c.observed_value):
            raise HTTPException(409,'REVIEW_HISTORY_INTEGRITY_FAILURE')
        expected_prev=all_events[ix-2].new_status if ix>1 else 'UNVERIFIED_OCR_CANDIDATE'
        if e.previous_status!=expected_prev:raise HTTPException(409,'INVALID_HISTORY_TRANSITION')
        chain=e.event_hash
    return all_events

def event_view(e):
    return {k:getattr(e,k) for k in ('id','candidate_id','organization_id','document_id','source_sha256',
        'page','bbox','observed_value','previous_status','new_status','new_value','reason',
        'reviewer_id','timestamp','version','operation_id','event_hash')}

class Demo:
    def __init__(self,workspace,a1_path):
        if os.getenv('MCIAS_ENVIRONMENT','development')=='production':
            raise RuntimeError('isolated demonstration cannot run in production')
        self.root=Path(workspace).resolve();self.root.mkdir(parents=True,exist_ok=True)
        os.environ['MCIAS_ENVIRONMENT']='development';os.environ['MCIAS_MALWARE_SCAN']='disabled'
        os.environ['MCIAS_LOCAL_OCR']='disabled'
        self.engine=create_engine('sqlite+pysqlite:///'+str(self.root/'pilot.sqlite3'),
                                  connect_args={'check_same_thread':False})
        Base.metadata.create_all(self.engine)
        with self.engine.begin() as db:
            for table in ('reader_isolated_review_events','reader_isolated_evidence_seal',
                          'reader_ocr_candidate_isolated'):
                db.execute(text(f'''CREATE TRIGGER IF NOT EXISTS {table}_immutable_update
                    BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END'''))
                db.execute(text(f'''CREATE TRIGGER IF NOT EXISTS {table}_immutable_delete
                    BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END'''))
        self.store=EncryptedStore(str(self.root/'sealed'),os.urandom(32))
        self.a1=load_a1(a1_path)
        self.tokens={};self.passwords={}
        self.cases={};self.parsed={}
        with Session(self.engine) as db:
            first=Organization(name='SYNTHETIC Hospital A')
            second=Organization(name='SYNTHETIC Hospital B')
            actor=User(username='reviewer-a',password_hash='synthetic-password-not-production')
            outsider=User(username='reviewer-b',password_hash='synthetic-password-not-production')
            db.add_all([first,second,actor,outsider]);db.flush()
            actor.organization_id=first.id;outsider.organization_id=second.id;db.commit()
            self.org_ids={'reviewer-a':first.id,'reviewer-b':second.id}
            self.passwords={'reviewer-a':'demo-reviewer-a-2026','reviewer-b':'demo-reviewer-b-2026'}
            for case,style in STYLES.items():
                gold=make_fixture(case,self.root)
                original=Path(gold['pdf_path']).read_bytes()
                # Page navigation exercised on 2-page image-only source. Page 1 retains OCR fields.
                if case=='english_columnar':
                    source=fitz.open(stream=original,filetype='pdf')
                    expanded=fitz.open();expanded.insert_pdf(source);expanded.insert_pdf(source)
                    original=expanded.tobytes();expanded.close();source.close()
                    gold['pdf_sha256']=hashlib.sha256(original).hexdigest()
                saved=ingest(db,self.store,first.id,actor.id,case+'.pdf',original)
                assert saved['status']=='review_required'
                reopened,doc,src=reopen(db,self.store,saved['document_id'],first.id,gold['pdf_sha256'])
                doc_for_ocr=fitz.open(stream=reopened,filetype='pdf')
                single=fitz.open();single.insert_pdf(doc_for_ocr,from_page=0,to_page=0)
                one_page=single.tobytes();single.close();doc_for_ocr.close()
                tmp=self.root/(case+'_ocr_page1.pdf');tmp.write_bytes(one_page)
                words,_=read_pixels_and_words(tmp,hashlib.sha256(one_page).hexdigest(),style['lang'])
                parsed=parse_dynamic(words,doc.id,doc.sha256,style['lang'])
                job=db.get(IngestionJob,saved['job_id'])
                count=create_candidates(db,doc,job,parsed)
                assert count==18
                db.flush()
                for candidate in all_candidates(db,first.id,doc.id):
                    db.add(EvidenceSeal(candidate_id=candidate.id,evidence_sha256=fingerprint(candidate)))
                db.commit()
                self.cases[case]={'doc':doc.id,'org':first.id,'sha':doc.sha256,'gold':gold}
                self.parsed[doc.id]=parsed

    def auth(self,authorization):
        token=(authorization or '').removeprefix('Bearer ').strip()
        user=self.tokens.get(token) if token else None
        if user is None:raise HTTPException(401,'LOGIN_REQUIRED')
        with Session(self.engine) as db:
            actor=db.get(User,user)
            if actor is None or not actor.active or not actor.organization_id:
                raise HTTPException(403,'REVIEWER_NOT_AUTHORIZED')
            return {'id':actor.id,'org':actor.organization_id}

    def source(self,db,doc_id,ctx):
        doc=db.scalar(select(IngestionDocument).where(
            IngestionDocument.id==doc_id,
            IngestionDocument.organization_id==ctx['org']))
        if not doc:raise HTTPException(404,'DOCUMENT_NOT_AVAILABLE')
        try:data,_,_=reopen(db,self.store,doc.id,ctx['org'],doc.sha256)
        except Exception:raise HTTPException(409,'ORIGINAL_SOURCE_INTEGRITY_FAILED')
        return doc,data

    def bound(self,db,cid,ctx):
        c=db.scalar(select(Candidate).where(Candidate.id==cid,
              Candidate.organization_id==ctx['org']))
        if not c:raise HTTPException(404,'CANDIDATE_NOT_AVAILABLE')
        doc,data=self.source(db,c.document_id,ctx)
        if doc.sha256!=c.source_sha256:raise HTTPException(409,'SOURCE_HASH_MISMATCH')
        pdf=fitz.open(stream=data,filetype='pdf')
        try:
            if c.page<1 or c.page>len(pdf) or len(c.bbox)!=4:raise HTTPException(409,'INVALID_PAGE')
            width,height=1650,1900
            x0,y0,x1,y1=c.bbox
            if not (0<=x0<x1<=width and 0<=y0<y1<=height):raise HTTPException(409,'INVALID_CELL_BBOX')
        finally:pdf.close()
        if ' '.join(w['text'] for w in c.ocr_words)!=c.observed_value:
            raise HTTPException(409,'OCR_EVIDENCE_VALUE_MISMATCH')
        if not all((w['bbox'][0]>=x0-3 and w['bbox'][2]<=x1+3 and
                    w['bbox'][1]>=y0-3 and w['bbox'][3]<=y1+3) for w in c.ocr_words):
            raise HTTPException(409,'WORD_COORDINATE_MISMATCH')
        return c

    def independently_verify(self,db,c,ctx):
        # PDF bytes are re-opened from native G2 for each evidence decision/export.
        _,data=self.source(db,c.document_id,ctx)
        pdf=fitz.open(stream=data,filetype='pdf')
        try:
            one=fitz.open();one.insert_pdf(pdf,from_page=c.page-1,to_page=c.page-1)
            source_page=one.tobytes();one.close()
        finally:pdf.close()
        with tempfile.TemporaryDirectory(prefix='reader-original-recheck-') as folder:
            p=Path(folder)/'page.pdf';p.write_bytes(source_page)
            case=next((name for name,info in self.cases.items() if info['doc']==c.document_id),None)
            if case is None:raise HTTPException(409,'UNKNOWN_SYNTHETIC_ORIGINAL')
            tokens,_=read_pixels_and_words(p,hashlib.sha256(source_page).hexdigest(),STYLES[case]['lang'])
            observed=parse_dynamic(tokens,c.document_id,c.source_sha256,STYLES[case]['lang'])
        matching=[r.get(c.field_name) for r in observed['rows'] if r.get('id') and r['id']['value']==c.row_id]
        if len(matching)!=1 or matching[0] is None:
            raise HTTPException(409,'REOPENED_ORIGINAL_ROW_NOT_FOUND')
        item=matching[0]
        if item['value']!=c.observed_value or item['bbox_pixels']!=c.bbox or item['ocr_word_evidence']!=c.ocr_words:
            raise HTTPException(409,'REOPENED_ORIGINAL_EVIDENCE_MISMATCH')
        return True

    def review(self,db,c,ctx,req):
        history=verify_history(db,c)
        self.independently_verify(db,c,ctx)
        request_hash=digest_json(req.model_dump())
        for e in history:
            if e.operation_id==req.operation_id:
                if e.request_sha256==request_hash and e.reviewer_id==ctx['id']:
                    return {'event':event_view(e),'idempotent_replay':True}
                raise HTTPException(409,'OPERATION_ID_REUSE_CONFLICT')
        if req.expected_version!=len(history):raise HTTPException(409,'STALE_EVIDENCE_VERSION')
        if req.action in ('correct','reject','unresolved') and len(req.reason.strip())<10:
            raise HTTPException(422,'REASON_REQUIRED')
        if req.action=='correct':
            if not req.corrected_value or not req.corrected_value.strip():
                raise HTTPException(422,'CORRECTION_VALUE_REQUIRED')
            if req.corrected_value.strip()==c.observed_value:
                raise HTTPException(422,'CORRECTION_MUST_DIFFER_FROM_OCR')
            new_value=req.corrected_value.strip()
        elif req.corrected_value is not None:
            raise HTTPException(422,'VALUE_ALLOWED_ONLY_FOR_CORRECTION')
        else:new_value=c.observed_value if req.action=='accept' else None
        if history and req.action in ('accept','correct') and len(req.reason.strip())<10:
            raise HTTPException(422,'REVIEW_REVISION_REASON_REQUIRED')
        prev=history[-1].new_status if history else 'UNVERIFIED_OCR_CANDIDATE'
        version=len(history)+1;previous_hash=history[-1].event_hash if history else '0'*64
        fields={'candidate_id':c.id,'organization_id':c.organization_id,'document_id':c.document_id,
          'source_sha256':c.source_sha256,'page':c.page,'bbox':c.bbox,'observed_value':c.observed_value,
          'previous_status':prev,'new_status':MAPPING[req.action],'new_value':new_value,
          'reason':req.reason.strip(),'reviewer_id':ctx['id'],
          'timestamp':datetime.now(timezone.utc).isoformat(),'version':version,
          'operation_id':req.operation_id,'request_sha256':request_hash,'previous_event_hash':previous_hash}
        e=ReviewEvent(**fields,event_hash=digest_json(fields))
        db.add(e)
        try:db.commit()
        except Exception:
            db.rollback();raise HTTPException(409,'CONCURRENT_EVIDENCE_VERSION_CONFLICT')
        return {'event':event_view(e),'idempotent_replay':False}

    def packet(self,db,doc_id,ctx):
        doc,data=self.source(db,doc_id,ctx)
        candidates=all_candidates(db,ctx['org'],doc.id)
        if len(candidates)!=18:return {'status':'HUMAN_REVIEW','blocked':['MISSING_OCR_FIELDS']}
        parsed=self.parsed[doc_id]
        if parsed['issues']:return {'status':'HUMAN_REVIEW','blocked':parsed['issues']}
        reviewed={}
        for c in candidates:
            self.bound(db,c.id,ctx)
            self.independently_verify(db,c,ctx)
            history=verify_history(db,c)
            if not history or history[-1].new_status not in FINAL:
                return {'status':'HUMAN_REVIEW','blocked':['FIELD_NOT_TRANSCRIPTION_ATTESTED']}
            reviewed[(c.row_id,c.field_name)]=history[-1].new_value
        # Build from source OCR fields and explicit human transcription-only revisions.
        data_rows=[]
        for row in parsed['rows']:
            one={}
            for k,val in row.items():
                one[k]=dict(val);one[k]['value']=reviewed[(row['id']['value'],k)]
            data_rows.append(one)
        updated={**parsed,'rows':data_rows}
        bundle=a1_payload(updated,'human-review-isolated')
        if not bundle:return {'status':'HUMAN_REVIEW','blocked':['UNSUPPORTED_A1_PREVIEW_INPUT']}
        result=self.a1.analyze(bundle)
        return {'status':'HUMAN_REVIEW','scope':'TRANSCRIPTION_REVIEW_ONLY',
                'a1_advisory':result,'a1_arithmetic_count':sum(
                 f['finding_type']=='LINE_ARITHMETIC' for f in result['findings']),
                'original_sha256_verified_local':True,'g2_trusted_ocr_rows':False,
                'extracted_rows_equal_original':False,'medical_service_approved':False,
                'financial_decision':'NOT_AUTHORIZED','source_verifications':[]}

LOGIN_HTML=Path(__file__).with_name('document_reader_human_review.html')

def create_app(demo):
    app=FastAPI(title='MCIAS synthetic G2 human review isolated',docs_url=None,redoc_url=None)
    def ctx(authorization: str|None=Header(default=None)):
        return demo.auth(authorization)
    @app.get('/',response_class=HTMLResponse)
    def page():
        return Response(LOGIN_HTML.read_text(encoding='utf-8'),media_type='text/html',
                        headers={'Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; object-src 'none'"})
    @app.post('/api/login')
    def login(data:dict):
        if set(data)!={'username','password'}:raise HTTPException(400,'LOGIN_FIELDS')
        user=data['username'];password=data['password']
        expected=demo.passwords.get(user)
        if not expected or not isinstance(password,str) or not secrets.compare_digest(expected,password):
            raise HTTPException(401,'LOGIN_FAILED')
        with Session(demo.engine) as db:
            actor=db.scalar(select(User).where(User.username==user,User.active==True))
            if not actor or actor.organization_id!=demo.org_ids[user]:raise HTTPException(403,'ACCOUNT_NOT_AUTHORIZED')
            token=secrets.token_urlsafe(32);demo.tokens[token]=actor.id
        return {'token':token,'role':'synthetic_transcription_reviewer'}
    @app.get('/api/documents')
    def documents(user=Depends(ctx)):
        with Session(demo.engine) as db:
            docs=db.scalars(select(IngestionDocument).where(IngestionDocument.organization_id==user['org'])).all()
            return [{'id':d.id,'filename':d.filename,'status':d.status} for d in docs]
    @app.get('/api/documents/{doc_id}/pages/{page_number}')
    def page_image(doc_id:str,page_number:int,user=Depends(ctx)):
        with Session(demo.engine) as db:doc,data=demo.source(db,doc_id,user)
        pdf=fitz.open(stream=data,filetype='pdf')
        try:
            if page_number<1 or page_number>len(pdf):raise HTTPException(404,'PAGE_NOT_FOUND')
            p=pdf[page_number-1].get_pixmap(matrix=fitz.Matrix(1650/612,1900/705),alpha=False)
            result=p.tobytes('png')
        finally:pdf.close()
        return Response(content=result,media_type='image/png',headers={'Cache-Control':'no-store'})
    @app.get('/api/documents/{doc_id}/evidence')
    def evidence(doc_id:str,user=Depends(ctx)):
        with Session(demo.engine) as db:
            doc,data=demo.source(db,doc_id,user)
            pdf=fitz.open(stream=data,filetype='pdf')
            try:count=len(pdf)
            finally:pdf.close()
            out=[]
            for c in all_candidates(db,user['org'],doc.id):
                demo.bound(db,c.id,user)
                hist=verify_history(db,c)
                out.append({'id':c.id,'row':c.row_id,'field':c.field_name,
                    'ocr_value':c.observed_value,'confidence_uncalibrated':c.ocr_confidence,
                    'bbox':c.bbox,'page':c.page,'original_sha256':c.source_sha256,
                    'status':hist[-1].new_status if hist else c.status,
                    'value':hist[-1].new_value if hist else c.observed_value,
                    'version':len(hist),'issue':None if hist and hist[-1].new_status in FINAL else 'HUMAN_REVIEW'})
            return {'document_id':doc.id,'page_count':count,'status':doc.status,
                    'trust':'OCR_TRANSCRIPTION_ONLY','fields':out}
    @app.post('/api/evidence/{candidate_id}/decision')
    def decision(candidate_id:str,req:Decision,user=Depends(ctx)):
        with Session(demo.engine) as db:
            c=demo.bound(db,candidate_id,user)
            return demo.review(db,c,user,req)
    @app.get('/api/documents/{doc_id}/review-export')
    def review_export(doc_id:str,user=Depends(ctx)):
        with Session(demo.engine) as db:
            doc,_=demo.source(db,doc_id,user)
            all_fields=[]
            for c in all_candidates(db,user['org'],doc.id):
                demo.bound(db,c.id,user);history=verify_history(db,c)
                all_fields.append({'candidate':c.id,'ocr_value':c.observed_value,
                    'original_sha256':c.source_sha256,'page':c.page,'bbox':c.bbox,
                    'events':[event_view(e) for e in history]})
            return {'document_id':doc.id,'source_sha256':doc.sha256,
                'reviewed_fields':all_fields,'source_attestation':'NOT_TRUSTED_G2_ROW',
                'transcription_only':True,'financial_decision':'NOT_AUTHORIZED'}
    @app.get('/api/documents/{doc_id}/a1-preview')
    def a1(doc_id:str,user=Depends(ctx)):
        with Session(demo.engine) as db:return demo.packet(db,doc_id,user)
    return app

def main():
    p=argparse.ArgumentParser();p.add_argument('--a1',required=True)
    p.add_argument('--workdir',required=True);p.add_argument('--port',type=int,default=8765)
    args=p.parse_args()
    demo=Demo(args.workdir,args.a1)
    import uvicorn
    uvicorn.run(create_app(demo),host='127.0.0.1',port=args.port,log_level='warning')
if __name__=='__main__':main()