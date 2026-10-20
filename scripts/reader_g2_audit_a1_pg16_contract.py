#!/usr/bin/env python3
"""Isolated PG16 contract verification against pinned PR29 writer and PR20 A1.

The contract event rows belong to a disposable test fixture; no Alembic/production
schema, no substitute audit service, no real claims, no medical/financial action.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, re, sys, tempfile, threading, uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from pydantic import BaseModel as Schema, ConfigDict, Field, ValidationError
from sqlalchemy import create_engine, select, inspect, text, String, Integer, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, Mapped, mapped_column
from mcias.models import Base, Organization, User, SessionToken, SourceFile, AuditLog, Role, Permission, RolePermission, UserRole, uid
from mcias.policy import has_permission
from mcias.models_ingestion import IngestionDocument, IngestionJob
from mcias.storage import EncryptedStore
from g2_trust_pilot import reopen
from g2_ocr_evidence_qualification_pilot import Candidate, create_candidates, all_candidates
from document_reader_dynamic_layout_pilot import (
    STYLES, PATTERNS, make_fixture, read_pixels_and_words, parse_dynamic, a1_payload, load_a1)
from reader_reviewed_ocr_contract import ReviewedOCREvidence, CellLocator, VersionRecord

class ReviewVersion(Base):
    """Business review version, NOT an audit writer or production table."""
    __tablename__="reader_review_version_test_only"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    organization_id: Mapped[str]=mapped_column(ForeignKey("organizations.id"),nullable=False)
    document_id: Mapped[str]=mapped_column(ForeignKey("ingestion_documents.id"),nullable=False)
    candidate_id: Mapped[str]=mapped_column(ForeignKey("reader_ocr_candidate_isolated.id"),nullable=False)
    reviewer_id: Mapped[str]=mapped_column(ForeignKey("users.id"),nullable=False)
    original_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    operation_id: Mapped[str]=mapped_column(String(96),nullable=False)
    request_digest: Mapped[str]=mapped_column(String(64),nullable=False)
    version: Mapped[int]=mapped_column(Integer,nullable=False)
    prior_state: Mapped[str]=mapped_column(String(48),nullable=False)
    state: Mapped[str]=mapped_column(String(48),nullable=False)
    corrected: Mapped[str|None]=mapped_column(String(300))
    reason_code: Mapped[str]=mapped_column(String(64),nullable=False)
    audit_event_id: Mapped[str]=mapped_column(ForeignKey("audit_log.id"),nullable=False)
    __table_args__=(UniqueConstraint("candidate_id","version"),
                    UniqueConstraint("candidate_id","operation_id"))

class Decision(Schema):
    model_config=ConfigDict(extra="forbid",strict=True)
    candidate_id: str
    expected_version: int=Field(ge=0)
    operation_id: str=Field(min_length=8,max_length=96)
    action: str
    corrected_value: str|None=None
    reason_code: str="none"

ACTIONS={"accept":"TRANSCRIPTION_ACCEPTED","correct":"TRANSCRIPTION_CORRECTED",
         "reject":"REJECTED","pending":"PENDING_HUMAN_REVIEW","unresolved":"UNRESOLVED"}
class ContractRejected(Exception):
    pass

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()

def pinned_writer(source):
    # Read-only imports from exact pinned PR29 directory. Its original code is executed.
    location=Path(source)
    for name,file in (("mcias.audit_contract","mcias/audit_contract.py"),
                      ("mcias.audit_writer","mcias/audit_writer.py")):
        spec=importlib.util.spec_from_file_location(name,location/file)
        module=importlib.util.module_from_spec(spec)
        sys.modules[name]=module
        spec.loader.exec_module(module)
    return sys.modules["mcias.audit_writer"]

def session_actor(db,token):
    hashed=hashlib.sha256(token.encode()).hexdigest()
    now=datetime.now(timezone.utc)
    active=db.scalar(select(SessionToken).where(SessionToken.token_hash==hashed,
        SessionToken.revoked_at.is_(None)))
    if active is None or active.expires_at.replace(tzinfo=timezone.utc)<now:
        raise ContractRejected("SESSION_NOT_AUTHORIZED")
    actor=db.get(User,active.user_id)
    if actor is None or not actor.active or not actor.organization_id:
        raise ContractRejected("REVIEWER_NOT_ACTIVE_IN_TENANT")
    if not has_permission(db,actor,"ingestion.review"):
        raise ContractRejected("REVIEWER_ROLE_PERMISSION_MISSING")
    return actor

def versions(db,cid):
    return db.scalars(select(ReviewVersion).where(ReviewVersion.candidate_id==cid)
        .order_by(ReviewVersion.version)).all()

def source_candidate(db,store,actor,cid,expected_sha):
    c=db.scalar(select(Candidate).where(Candidate.id==cid,Candidate.organization_id==actor.organization_id))
    if not c:raise ContractRejected("CROSS_TENANT_OR_MISSING_CANDIDATE")
    try:
        data,doc,src=reopen(db,store,c.document_id,actor.organization_id,expected_sha)
    except Exception as exc:raise ContractRejected("ORIGINAL_G2_SOURCE_INVALID") from exc
    if (c.source_sha256!=doc.sha256 or doc.status!="review_required"
        or c.status!="UNVERIFIED_OCR_CANDIDATE"
        or c.page!=1 or len(c.bbox)!=4 or not c.ocr_words
        or c.observed_value!=" ".join(w["text"] for w in c.ocr_words)):
        raise ContractRejected("UNVERIFIED_CANDIDATE_CHANGED")
    job=db.scalar(select(IngestionJob).where(
        IngestionJob.id==c.job_id, IngestionJob.document_id==doc.id,
        IngestionJob.organization_id==actor.organization_id))
    if job is None:raise ContractRejected("OCR_JOB_DOCUMENT_OR_TENANT_MISMATCH")
    a,b,x,y=c.bbox
    if not(0<=a<x<=1650 and 0<=b<y<=1900):
        raise ContractRejected("OCR_SOURCE_REGION_INVALID")
    return c,doc

def submit(engine,store,writer,token,req,source_hash,*,reject_audit=True):
    if isinstance(req,dict):req=Decision.model_validate(req)
    if req.action not in ACTIONS:raise ContractRejected("INVALID_TRANSCRIPTION_ACTION")
    event_digest=digest(req.model_dump())
    with Session(engine) as db:
        actor=session_actor(db,token)
        actor_id,own_org=actor.id,actor.organization_id
        try:
            # Lock the G2 document row for transaction-scoped review serialization.
            c0=db.scalar(select(Candidate).where(Candidate.id==req.candidate_id,
                Candidate.organization_id==own_org))
            if c0 is None:raise ContractRejected("CROSS_TENANT_OR_MISSING_CANDIDATE")
            doc=db.scalar(select(IngestionDocument).where(
                IngestionDocument.id==c0.document_id,
                IngestionDocument.organization_id==own_org).with_for_update())
            if doc is None:raise ContractRejected("SOURCE_TENANT_MISMATCH")
            c,doc=source_candidate(db,store,actor,req.candidate_id,source_hash)
            existing=versions(db,c.id)
            for event in existing:
                if event.operation_id==req.operation_id:
                    if event.request_digest==event_digest and event.reviewer_id==actor_id:
                        return {"version":event.version,"audit_event_id":event.audit_event_id,"replay":True}
                    raise ContractRejected("OPERATION_REUSE_CONFLICT")
            if req.expected_version!=len(existing):raise ContractRejected("STALE_REVIEW_VERSION")
            if req.action=="correct":
                if (not req.corrected_value or req.corrected_value==c.observed_value
                    or not re.fullmatch(PATTERNS[c.field_name],req.corrected_value)
                    or req.reason_code not in ("transcription_error","synthetic_price_correction","unclear_source")):
                    raise ContractRejected("CORRECTION_NEEDS_VALUE_AND_REASON")
            elif req.corrected_value is not None:
                raise ContractRejected("UNAUTHORIZED_FIELD_VALUE")
            previous=existing[-1].state if existing else "UNVERIFIED_OCR_CANDIDATE"
            current=ACTIONS[req.action]
            audit=writer.write_event(db,actor=actor,organization_id=own_org,
                action="ocr_transcription_"+req.action,resource_type="ocr_candidate",
                resource_id=c.id,outcome="success",
                details={"version":len(existing)+1,"status":"pending",
                         "patient_name":"SYNTHETIC_NEVER_LOG",
                         "amount":"999999","source_sha256":source_hash})
            ev=ReviewVersion(organization_id=own_org,document_id=c.document_id,
                candidate_id=c.id,reviewer_id=actor_id,original_sha256=c.source_sha256,
                operation_id=req.operation_id,request_digest=event_digest,
                version=len(existing)+1,prior_state=previous,state=current,
                corrected=req.corrected_value,reason_code=req.reason_code,
                audit_event_id=audit.id)
            db.add(ev);db.commit()
            return {"version":ev.version,"audit_event_id":audit.id,"replay":False}
        except ContractRejected as err:
            db.rollback()
            if reject_audit and err.args and err.args[0] not in ("OPERATION_REUSE_CONFLICT","STALE_REVIEW_VERSION"):
                writer.record_outcome_independent(engine,actor_id=actor_id,
                    organization_id=own_org,action="ocr_transcription_denied",
                    resource_type="ocr_candidate",resource_id=None,outcome="denied",
                    details={"reason_code":"permission_denied"})
            raise

def qualified(db,store,actor,doc_id):
    """Strict test projection, no G2 trusted-row or service verification assertion."""
    doc=db.scalar(select(IngestionDocument).where(IngestionDocument.id==doc_id,
                  IngestionDocument.organization_id==actor.organization_id))
    if doc is None:raise ContractRejected("TENANT_SOURCE_NOT_FOUND")
    candidates=all_candidates(db,actor.organization_id,doc_id)
    if len(candidates)!=18:return None,["INCOMPLETE_OCR_FIELDS"]
    out=[];by_row={}
    for c in candidates:
        c,original=source_candidate(db,store,actor,c.id,doc.sha256)
        history=versions(db,c.id)
        if not history or history[-1].state not in (
                "TRANSCRIPTION_ACCEPTED","TRANSCRIPTION_CORRECTED"):
            return None,["TRANSCRIPTION_NOT_ATTESTED"]
        before="UNVERIFIED_OCR_CANDIDATE";versioned=[]
        for i,v in enumerate(history,1):
            if v.version!=i or v.prior_state!=before or v.original_sha256!=doc.sha256:
                raise ContractRejected("REVIEW_VERSION_LINEAGE_INVALID")
            log=db.get(AuditLog,v.audit_event_id)
            if (log is None or log.actor_id!=v.reviewer_id
                or log.resource_id!=c.id or log.details.get("organization_id")!=doc.organization_id
                or log.details.get("outcome")!="success"):
                raise ContractRejected("SHARED_AUDIT_REFERENCE_INVALID")
            versioned.append(VersionRecord(version=v.version,operation_id=v.operation_id,
                audit_event_id=v.audit_event_id,reviewer_user_id=v.reviewer_id,
                from_state=v.prior_state,to_state=v.state,corrected_value=v.corrected,
                reason_code=v.reason_code,event_id=v.id))
            before=v.state
        last=history[-1];value=last.corrected if last.state=="TRANSCRIPTION_CORRECTED" else c.observed_value
        item=ReviewedOCREvidence(organization_id=doc.organization_id,document_id=doc.id,
            job_id=c.job_id,candidate_id=c.id,original_sha256=doc.sha256,
            row_id=c.row_id,field_name=c.field_name,
            locator=CellLocator(page=c.page,bbox_pixels=tuple(c.bbox)),
            ocr_value=c.observed_value,reviewed_value=value,
            uncalibrated_ocr_confidence=c.ocr_confidence,
            transcription_status=last.state,versions=versioned,
            source_original_bytes_sha256_checked=True)
        out.append(item)
        by_row.setdefault(c.row_id,{})[c.field_name]=value
    return (out,by_row),[]

def advisory(db,store,actor,doc_id,parsed,a1):
    checked,issues=qualified(db,store,actor,doc_id)
    if issues:return {"status":"HUMAN_REVIEW","blocked":issues,"financial_decision":"NOT_AUTHORIZED"}
    items,by_row=checked
    if any(len(fields)!=6 for fields in by_row.values()):
        return {"status":"HUMAN_REVIEW","blocked":["MISSING_ITEMS"],"financial_decision":"NOT_AUTHORIZED"}
    rows=[]
    for row in parsed["rows"]:
        rid=row["id"]["value"]
        clone={k:{**field,"value":by_row[rid][k]} for k,field in row.items()}
        rows.append(clone)
    bundle=a1_payload({**parsed,"rows":rows},"pg16-reviewed-ocr-only")
    if bundle is None:return {"status":"HUMAN_REVIEW","blocked":["A1_PREVIEW_BUNDLE_BLOCKED"],
                               "financial_decision":"NOT_AUTHORIZED"}
    result=a1.analyze(bundle)
    return {"status":"HUMAN_REVIEW","reviewed_evidence_count":len(items),
            "a1_arithmetic_count":sum(x["finding_type"]=="LINE_ARITHMETIC"
                                      for x in result["findings"]),
            "source_verifications":[],"g2_native_rows_verified":False,
            "a1_trusted_adapter_used":False,
            "clinical_service_verified":False,"financial_decision":"NOT_AUTHORIZED"}

def expect_rejection(func,part,negative):
    try:func()
    except (ContractRejected,ValidationError):negative.append(part);return
    raise AssertionError("UNSAFE_ACCEPT_"+part)

def run(outdir,url,pr29,pr20):
    if os.environ.get("MCIAS_READER_PG16_ISOLATED")!="YES":
        raise RuntimeError("explicit PG16 test consent required")
    p=urlsplit(url.replace("postgresql+psycopg://","postgresql://",1))
    if p.scheme!="postgresql" or p.hostname not in ("127.0.0.1","localhost") or p.path!="/mcias_reader_contract":
        raise RuntimeError("refusing non-disposable PostgreSQL endpoint")
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    writer=pinned_writer(pr29)
    a1=load_a1(Path(pr20)/"mcias/agents/invoice_integrity.py")
    engine=create_engine(url,pool_size=8,max_overflow=4)
    tables=[Organization.__table__,User.__table__,Role.__table__,
       Permission.__table__,RolePermission.__table__,UserRole.__table__,
       SessionToken.__table__,SourceFile.__table__,IngestionDocument.__table__,
       IngestionJob.__table__,AuditLog.__table__,Candidate.__table__,ReviewVersion.__table__]
    assert not any(inspect(engine).has_table(t.name) for t in tables),"disposable DB must start empty"
    Base.metadata.create_all(engine,tables=tables)
    # Test-owned domain record immutability in PostgreSQL, not a migration.
    with engine.begin() as conn:
        conn.execute(text("""CREATE FUNCTION reader_isolated_no_change() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'TEST_APPEND_ONLY'; END $$"""))
        for name in ("reader_review_version_test_only","reader_ocr_candidate_isolated"):
            conn.execute(text(f"""CREATE TRIGGER reader_pg_only_{name}
                BEFORE UPDATE OR DELETE ON {name}
                FOR EACH ROW EXECUTE FUNCTION reader_isolated_no_change()"""))
    negative=[];measure=[]
    os.environ["MCIAS_ENVIRONMENT"]="development"
    with tempfile.TemporaryDirectory(prefix="mcias-reader-pg16-") as temp:
        store=EncryptedStore(str(Path(temp)/"sealed"),os.urandom(32))
        with Session(engine) as db:
            org=Organization(name="SYNTHETIC-PG16-A")
            foreign=Organization(name="SYNTHETIC-PG16-B")
            db.add_all([org,foreign]);db.flush()
            actor=User(username="pg16-ocr-reviewer",organization_id=org.id,password_hash="fixture")
            outsider=User(username="pg16-foreign",organization_id=foreign.id,password_hash="fixture")
            powerless=User(username="pg16-no-role",organization_id=org.id,password_hash="fixture")
            role=Role(code="synthetic_ocr_transcription_reviewer")
            grant=Permission(code="ingestion.review")
            db.add_all([actor,outsider,powerless,role,grant]);db.flush()
            db.add(RolePermission(role_id=role.id,permission_id=grant.id))
            db.add_all([UserRole(user_id=actor.id,role_id=role.id),
                        UserRole(user_id=outsider.id,role_id=role.id)])
            tokens={}
            for user,secret in [(actor,"synthetic-ocr-actor-token"),
                                (outsider,"synthetic-foreign-token"),
                                (powerless,"synthetic-no-role-token")]:
                db.add(SessionToken(user_id=user.id,token_hash=hashlib.sha256(secret.encode()).hexdigest(),
                    expires_at=datetime.now(timezone.utc)+timedelta(hours=1)))
                tokens[user.username]=secret
            db.commit()
            primary_org,second_org=org.id,foreign.id
            cases={}
            for case in ("english_columnar","english_reordered"):
                gold=make_fixture(case,out)
                data=Path(gold["pdf_path"]).read_bytes()
                storage_key,sha=store.put(data)
                src=SourceFile(sha256=sha,original_filename=case+".pdf",storage_key=storage_key)
                db.add(src);db.flush()
                doc=IngestionDocument(organization_id=primary_org,source_id=src.id,
                    sha256=sha,filename=case+".pdf",status="review_required")
                db.add(doc);db.flush()
                job=IngestionJob(organization_id=primary_org,document_id=doc.id,
                    status="review_required",manifest={"complete":False,"synthetic":True})
                db.add(job);db.flush()
                restored,_,_=reopen(db,store,doc.id,primary_org,sha)
                assert restored==data
                source=out/(case+"_from_G2.pdf");source.write_bytes(restored)
                words,_=read_pixels_and_words(source,sha,STYLES[case]["lang"])
                parsed=parse_dynamic(words,doc.id,sha,STYLES[case]["lang"])
                assert not parsed["issues"],parsed["issues"]
                assert create_candidates(db,doc,job,parsed)==18
                db.commit()
                cases[case]={"doc":doc.id,"sha":sha,"parsed":parsed,"storage_key":storage_key}
        token=tokens["pg16-ocr-reviewer"]
        outsider_token=tokens["pg16-foreign"]
        powerless_token=tokens["pg16-no-role"]
        with Session(engine) as db:
            first=all_candidates(db,primary_org,cases["english_columnar"]["doc"])[0]
            cid=first.id
            actor=db.get(User,db.scalar(select(User.id).where(User.username=="pg16-ocr-reviewer")))
            missing=advisory(db,store,actor,cases["english_columnar"]["doc"],
                             cases["english_columnar"]["parsed"],a1)
            assert missing["blocked"]==["TRANSCRIPTION_NOT_ATTESTED"]
        def req(c,operation,version=0,action="accept",**kwargs):
            return {"candidate_id":c,"expected_version":version,"operation_id":operation,
                    "action":action,**kwargs}
        expect_rejection(lambda:Decision.model_validate(
             {**req(cid,"reject-identity-01"),"reviewer_id":"forged"}),"FAKE_CLIENT_ACTOR",negative)
        expect_rejection(lambda:submit(engine,store,writer,powerless_token,
            req(cid,"denied-missing-role"),cases["english_columnar"]["sha"]),"UNGRANTED_REVIEW_PERMISSION",negative)
        expect_rejection(lambda:submit(engine,store,writer,outsider_token,
            req(cid,"denied-foreign-ten"),cases["english_columnar"]["sha"]),"CROSS_ORGANIZATION",negative)
        expect_rejection(lambda:submit(engine,store,writer,token,
            req(cid,"wrong-hash-source"),"0"*64),"ORIGINAL_DIGEST_TAMPERED",negative)
        # Genuine concurrency against same PostgreSQL row and version.
        x=req(cid,"concurrent-operation-0001")
        y=req(cid,"concurrent-operation-0002")
        def attempt(payload):
            try:return submit(engine,store,writer,token,payload,cases["english_columnar"]["sha"])
            except ContractRejected as e:return {"rejected":str(e)}
        with ThreadPoolExecutor(max_workers=2) as pool:
            a,b=pool.map(attempt,(x,y))
        assert sorted([bool(z.get("replay") is False) for z in (a,b)])==[False,True],(a,b)
        assert sum(z.get("rejected")=="STALE_REVIEW_VERSION" for z in (a,b))==1,(a,b)
        negative.append("CONCURRENT_VERSION_CONFLICT")
        winning=x if a.get("replay") is False else y
        repeat=submit(engine,store,writer,token,winning,cases["english_columnar"]["sha"])
        assert repeat["replay"] is True and repeat["audit_event_id"]==(a if winning is x else b)["audit_event_id"]
        negative.append("IDEMPOTENT_DUPLICATE")
        expect_rejection(lambda:submit(engine,store,writer,token,
            {**winning,"action":"reject"},cases["english_columnar"]["sha"]),
            "OPERATION_PAYLOAD_REUSE",negative)
        with Session(engine) as db:
            c=db.get(Candidate,cid)
            target=store.root/cases["english_columnar"]["storage_key"]
            pristine=target.read_bytes()
            corrupted=bytearray(pristine);corrupted[-1]^=1
            try:
                target.write_bytes(corrupted)
                expect_rejection(lambda:submit(engine,store,writer,token,
                    req(cid,"tampered-ciphertext",version=1),cases["english_columnar"]["sha"]),
                    "ENCRYPTED_ORIGINAL_TAMPERED",negative)
            finally:target.write_bytes(pristine)
            # Direct SQL bypass attempt must be blocked by test-owned PG trigger.
            try:
                db.execute(text("UPDATE reader_review_version_test_only SET state='TRUSTED' WHERE candidate_id=:cid"),
                           {"cid":cid})
                db.commit()
            except Exception:
                db.rollback();negative.append("DIRECT_REVIEW_HISTORY_MUTATION")
            else:raise AssertionError("PG review history was rewritten")
            try:
                db.execute(text("UPDATE reader_ocr_candidate_isolated SET observed_value='999' WHERE id=:cid"),
                           {"cid":cid})
                db.commit()
            except Exception:
                db.rollback();negative.append("DIRECT_SOURCE_CANDIDATE_TAMPER")
            else:raise AssertionError("PG candidate evidence was rewritten")
        for case,info in cases.items():
            with Session(engine) as db:
                cs=all_candidates(db,primary_org,info["doc"])
                ids=[z.id for z in cs]
                price_hold=next((z.id for z in cs if z.row_id=="BB" and z.field_name=="price"),None)
            for c in ids:
                if case=="english_columnar" and c in (cid,price_hold):continue
                saved=submit(engine,store,writer,token,req(c,str(uuid.uuid4())),info["sha"])
                assert saved["version"]==1 and not saved["replay"]
            if case=="english_columnar":
                with Session(engine) as db:
                    active_actor=db.scalar(select(User).where(User.username=="pg16-ocr-reviewer"))
                    suspended=advisory(db,store,active_actor,info["doc"],info["parsed"],a1)
                    assert suspended["blocked"]==["TRANSCRIPTION_NOT_ATTESTED"]
                    negative.append("MISSING_PRICE_REVIEW_HOLDS_A1")
                approved=submit(engine,store,writer,token,req(price_hold,str(uuid.uuid4())),info["sha"])
                assert approved["version"]==1
            with Session(engine) as db:
                actor=db.scalar(select(User).where(User.username=="pg16-ocr-reviewer"))
                report=advisory(db,store,actor,info["doc"],info["parsed"],a1)
                expected=0 if case=="english_columnar" else 2
                assert report["a1_arithmetic_count"]==expected,report
                reviewed,holds=qualified(db,store,actor,info["doc"])
                assert not holds and len(reviewed[0])==18
                contract=reviewed[0][0]
                assert contract.versions[0].audit_event_id
                assert not contract.a1_trusted_input_eligible and not contract.g2_native_rows_verified
                logs=db.scalars(select(AuditLog).where(
                     AuditLog.resource_type=="ocr_candidate",AuditLog.resource_id.in_(ids))).all()
                assert len([x for x in logs if x.details.get("outcome")=="success"])==18
                assert all("amount" not in x.details and "patient_name" not in x.details
                           and "source_sha256" not in x.details for x in logs)
                measure.append({"case":case,"reviewed_fields":18,
                    "shared_audit_success":len(logs),"a1_arithmetic":expected,
                    "contract_sample":contract.model_dump(mode="json"),
                    "financial_decision":"NOT_AUTHORIZED"})
        # Actual PR29 independent denial path must record only server-owned actor/tenant,
        # after denied business review rolls back.
        with Session(engine) as db:
            denials=db.scalars(select(AuditLog).where(
                AuditLog.action=="ocr_transcription_denied")).all()
            assert len(denials)>=2,denials
            assert all(row.details.get("reason_code")=="permission_denied" and
                       row.details.get("outcome")=="denied" and
                       "amount" not in row.details and "patient_name" not in row.details
                       for row in denials)
            foreign_actor=db.scalar(select(User).where(User.username=="pg16-foreign"))
            assert any(row.actor_id==foreign_actor.id and
                       row.details.get("organization_id")==second_org for row in denials)
            negative.append("ORIGINAL_SHARED_AUDIT_INDEPENDENT_DENIAL")
        # One correction preserves old event and creates exactly one new audit reference.
        with Session(engine) as db:
            c=db.scalar(select(Candidate).where(
                Candidate.organization_id==primary_org,
                Candidate.document_id==cases["english_columnar"]["doc"],
                Candidate.row_id=="AA",Candidate.field_name=="price"))
            price_id=c.id
        expect_rejection(lambda:submit(engine,store,writer,token,
            req(price_id,str(uuid.uuid4()),version=1,action="correct",
                corrected_value="NOT_A_PRICE",reason_code="synthetic_price_correction"),
            cases["english_columnar"]["sha"]),
            "NON_NUMERIC_PRICE_CORRECTION",negative)
        corrected=submit(engine,store,writer,token,
            req(price_id,str(uuid.uuid4()),version=1,action="correct",
                corrected_value="16.00",reason_code="synthetic_price_correction"),
            cases["english_columnar"]["sha"])
        assert corrected["version"]==2
        with Session(engine) as db:
            actor=db.scalar(select(User).where(User.username=="pg16-ocr-reviewer"))
            revised=advisory(db,store,actor,cases["english_columnar"]["doc"],
                cases["english_columnar"]["parsed"],a1)
            assert revised["a1_arithmetic_count"]==1
            hist=versions(db,price_id)
            assert len(hist)==2 and hist[0].state=="TRANSCRIPTION_ACCEPTED"
            assert hist[1].state=="TRANSCRIPTION_CORRECTED"
            assert hist[0].audit_event_id!=hist[1].audit_event_id
        # Actual trusted A1 PDF adapter is not invoked or bypassed by this contract.
        from pydantic import ValidationError as PydanticValidationError
        from importlib.util import spec_from_file_location,module_from_spec
        # Exact SourceVerification shape cannot be satisfied by OCR review alone.
        # Isolated source verifier is separately pinned in the A1 contract probe.
        summary={"status":"PG16_REVIEW_SHARED_AUDIT_A1_ADVISORY_VERIFIED",
                 "reviewed_document_count":len(cases),
                 "reviewed_field_count":36,
                 "original_audit_writer":"PR29_PINNED_UNMODIFIED",
                 "a1_analyzer":"PR20_PINNED_UNMODIFIED",
                 "negative_checks":negative,
                 "reviewed_cases":measure,
                 "after_correction_a1_arithmetic":revised["a1_arithmetic_count"],
                 "g2_trusted_pdf_rows":False,
                 "a1_trusted_input_used":False,
                 "medical_service_verified":False,
                 "tariff_verified":False,
                 "financial_decision":"NOT_AUTHORIZED",
                 "session_permissions_checked":True,
                 "shared_audit_operationally_approved":False}
        (out/"pg16_readiness_evidence.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2))
        print(json.dumps({"gate":summary["status"],"reviewed_fields":36,
            "negatives":negative,"advisory":[x["a1_arithmetic"] for x in measure],
            "after_correction":1}))
    Base.metadata.drop_all(engine,tables=list(reversed(tables)))
    with engine.begin() as conn:
        conn.execute(text("DROP FUNCTION IF EXISTS reader_isolated_no_change()"))
    engine.dispose()

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--database-url",required=True)
    ap.add_argument("--audit-checkout",required=True)
    ap.add_argument("--a1-checkout",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    run(a.out,a.database_url,a.audit_checkout,a.a1_checkout)
